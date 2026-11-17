"""Verify the published validation and ETL evidence, optionally against a rerun or CI ZIPs."""

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import median
from zipfile import BadZipFile, ZipFile

from phase_04_snapshot import ARCHIVE_SHA256, DECISION_SHA256, ROOT, snapshot, validation_summary

SOURCE_SHA256 = "f2de838bd0ef569a700976922711e2955fe057f806822a95a721ca55bdaa8080"
BENCHMARK_ARCHIVE_SHA256 = "80a647efed0065983f1dad286c863b1077c6efc07e5a693df7cf24570fdbdca8"
PUBLISHED_REPORTS = {
    "local_benchmark.json": ([1, 10, 100], "local[2]"),
    "ci_local_benchmark.json": ([1], "local[2]"),
    "ci_standalone_benchmark.json": ([1], "spark://master:7077"),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_validation(published: dict) -> None:
    require(published["source"]["archive_sha256"] == ARCHIVE_SHA256
            and published["source"]["csv_sha256"] == SOURCE_SHA256,
            "Published validation provenance differs from the pinned source")
    dataset = published["dataset"]
    require((dataset["rows"], dataset["class_counts"]["1"], dataset["duplicate_rows"])
            == (284_807, 492, 1_081), "Unexpected original-data inventory")
    parts = published["partitions"]
    require(sum(part["rows"] for part in parts.values()) == dataset["rows"]
            and sum(part["class_counts"]["1"] for part in parts.values()) == 492,
            "Chronological split inventory does not match the dataset")
    candidate, models = published["candidate"], published["models"]
    require(candidate["decision_sha256"] == DECISION_SHA256
            and candidate["test_opened"] is False, "Expected the published sealed proposal")
    require(len(models) == len({model["model"] for model in models}) == 11,
            "Expected 11 distinct validation configurations")
    winner = min(models, key=lambda model: (-model["average_precision"], -model["f2"], model["model"]))
    metrics = candidate["metrics"]
    require(winner["model"] == candidate["model_name"]
            and all(metrics[key] == winner[key]
                    for key in ("average_precision", "precision", "recall", "f2")),
            "Candidate differs from the best validation configuration")
    (tn, fp), (fn, tp) = metrics["confusion_matrix"]
    require(tn + fp + fn + tp == parts["validation"]["rows"]
            and fn + tp == parts["validation"]["class_counts"]["1"]
            and math.isclose(metrics["precision"], tp / (tp + fp))
            and math.isclose(metrics["recall"], tp / (tp + fn))
            and math.isclose(metrics["f2"], 5 * tp / (5 * tp + 4 * fn + fp)),
            "Validation metrics disagree with the confusion matrix or split inventory")


def verify_benchmark(report: dict, reference: dict, scales: list[int], master: str) -> None:
    require(report["completed"] is True and report["source_csv_sha256"] == SOURCE_SHA256
            and report["purpose"] == "etl_only" and report["environment"]["spark_master"] == master
            and report["config"]["scales"] == scales
            and [result["scale"] for result in report["results"]] == scales,
            "ETL report has unexpected source, workload, or execution mode")
    for result in report["results"]:
        scale = result["scale"]
        expected_counts = [[hour, label, count * scale]
                           for hour, label, count in reference["hour_class_counts"]]
        require(result["parity"] == {"rows": reference["rows"] * scale,
                                     "fraud_rows": reference["fraud_rows"] * scale,
                                     "hour_class_counts": expected_counts},
                f"{scale}x ETL parity differs from the verified 1x reference")
        for engine in ("pandas", "spark"):
            measurements = result["measurements"][engine]
            if engine == "spark" and master.startswith("spark://"):
                require(all(run["spark_registered_executors"] == 2 for run in measurements),
                        "Expected two registered Spark standalone executors")
            times = [run["elapsed_seconds"] for run in measurements]
            require(len(times) == report["config"]["repeats"] and bool(times)
                    and all(math.isfinite(seconds) and seconds > 0 for seconds in times)
                    and median(times) == result["summary"][engine]["median_elapsed_seconds"],
                    f"{scale}x {engine} median differs from the recorded measurements")


def verify_validation_rerun(directory: Path, published: dict) -> None:
    proposal = read_json(directory / "candidate_proposal.json")
    split = read_json(directory / "split_manifest.json")
    experiment = read_json(directory / "experiment.json")
    acceptance = read_json(directory / "acceptance.json")
    require(acceptance["technical_pipeline_passed"] is True
            and acceptance["test_opened"] is False and acceptance["candidate"] == proposal
            and acceptance["split_sha256"] == split["split_sha256"] == proposal["split_sha256"]
            and split["dataset"]["original_csv_sha256"] == SOURCE_SHA256,
            "Rerun acceptance, candidate and source disagree")
    actual = validation_summary(proposal, split, experiment)
    require(actual == {key: published[key] for key in actual},
            "Rerun differs from published validation evidence. Check the runtime, source and code.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase2-archive", type=Path, help="Original Phase 2 Actions ZIP")
    parser.add_argument("--phase3-archive", type=Path, help="Original Phase 3 Actions ZIP")
    parser.add_argument("--phase2-dir", type=Path, help="Phase 2 rerun output directory")
    parser.add_argument("--benchmark", type=Path, action="append", default=[],
                        help="ETL rerun JSON, repeat for multiple reports")
    args = parser.parse_args()

    reports_dir = ROOT / "reports/phase_03"
    try:
        published = read_json(ROOT / "dashboard/phase_02_snapshot.json")
        reference = read_json(reports_dir / "ci_local_benchmark.json")["results"][0]["parity"]
        verify_validation(published)
        for name, (scales, master) in PUBLISHED_REPORTS.items():
            verify_benchmark(read_json(reports_dir / name), reference, scales, master)
        if args.phase2_archive:
            require(snapshot(args.phase2_archive) == published,
                    "Pinned Phase 2 archive does not regenerate the published dashboard JSON")
        if args.phase3_archive:
            digest = hashlib.sha256(args.phase3_archive.read_bytes()).hexdigest()
            require(digest == BENCHMARK_ARCHIVE_SHA256, "Unexpected Phase 3 ZIP SHA-256")
            with ZipFile(args.phase3_archive) as bundle:
                for archived, published_name in (("benchmark.json", "ci_local_benchmark.json"),
                                                 ("standalone.json", "ci_standalone_benchmark.json")):
                    require(bundle.read(archived) == (reports_dir / published_name).read_bytes(),
                            f"{published_name} differs from its pinned archive")
        if args.phase2_dir:
            verify_validation_rerun(args.phase2_dir, published)
        for path in args.benchmark:
            report = read_json(path)
            verify_benchmark(report, reference, report["config"]["scales"],
                             report["environment"]["spark_master"])
    except (ArithmeticError, BadZipFile, IndexError, KeyError, OSError, TypeError, ValueError) as exc:
        parser.exit(1, f"Evidence verification failed: {exc}\n")
    print(json.dumps({
        "published_evidence_verified": True,
        "phase2_archive_verified": args.phase2_archive is not None,
        "phase3_archive_verified": args.phase3_archive is not None,
        "phase2_rerun_verified": args.phase2_dir is not None,
        "etl_reruns_verified": len(args.benchmark),
        "decision_sha256": published["candidate"]["decision_sha256"],
        "test_opened_in_published_evidence": published["candidate"]["test_opened"],
    }, indent=2))


if __name__ == "__main__":
    main()
