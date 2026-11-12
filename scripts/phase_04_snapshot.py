"""Build the dashboard's aggregate snapshot from the verified Phase 2 CI archive."""

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
RUN_URL = "https://github.com/ManhT005/credit-card-fraud-bigdata/actions/runs/42364868665"
ARCHIVE_SHA256 = "77fde42ecdc3ff1cf11790e535840aea7126f051f9d5c221959c451527b6edc9"
DECISION_SHA256 = "1602082a03abe686b8c828bc3bbac9711163461fcec65e459f51e6da4dafe00a"
METRICS = ("average_precision", "precision", "recall", "f2", "threshold", "confusion_matrix")


def snapshot(archive: Path) -> dict:
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("Archive SHA-256 differs from the verified Phase 2 artifact")
    with ZipFile(archive) as bundle:
        acceptance = json.loads(bundle.read("acceptance.json"))
        proposal = json.loads(bundle.read("candidate_proposal.json"))
        split = json.loads(bundle.read("split_manifest.json"))
        experiment = json.loads(bundle.read("experiment.json"))

    if (not acceptance["technical_pipeline_passed"] or acceptance["candidate"] != proposal
            or proposal["decision_sha256"] != DECISION_SHA256
            or any(item["test_opened"] for item in (acceptance, proposal, split, experiment))):
        raise ValueError("Expected the validated proposal with its held-out test sealed")

    runs = experiment["runs"]
    selected = next(run for run in runs if run["run_id"] == proposal["run_id"])
    if (selected["validation_metrics"] != proposal["threshold_policy"]["metrics"]
            or any(run["evaluation_source"] != "validation" for run in runs)):
        raise ValueError("Expected chronological validation metrics")
    dataset = split["dataset"]
    return {
        "source": {"run_url": RUN_URL, "archive_sha256": ARCHIVE_SHA256,
                   "csv_sha256": dataset["original_csv_sha256"]},
        "dataset": {name: dataset[name] for name in ("rows", "class_counts", "duplicate_rows")},
        "partitions": {
            name: {key: part[key] for key in ("rows", "class_counts")}
            for name, part in split["audit"]["partitions"].items()
        },
        "candidate": {
            **{key: proposal[key] for key in ("model_name", "decision_sha256", "status")},
            "test_opened": False,
            "metrics": {key: selected["validation_metrics"][key] for key in METRICS},
            "pr_curve": {key: selected["curves"][key] for key in ("precision", "recall")},
        },
        "models": [
            {"model": run["model_name"],
             **{key: run["validation_metrics"][key] for key in METRICS[:4]}}
            for run in runs
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    evidence = snapshot(args.archive)
    (ROOT / "dashboard/phase_02_snapshot.json").write_text(
        json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
