"""Original-source Phase 2 technical gate; researcher sign-off is never fabricated."""

import argparse
import json
import os
from pathlib import Path

import nbformat
from nbclient import NotebookClient

from fraud_detection.pipelines.train import code_revision, load_config, run_from_root
from fraud_detection.preprocessing.manifest import write_json

ROOT = Path(__file__).resolve().parents[1]


def save_executed_notebook(document, destination: Path) -> None:
    """Support a clean checkout where the artifact directory does not exist yet."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(document, destination)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-source", action="store_true",
                        help="Reacquire pinned source; require existing successful Phase 1 evidence")
    parser.add_argument("--execute-notebooks", action="store_true",
                        help="Execute all four notebooks from root and notebooks/ using kernels")
    args = parser.parse_args()
    output = ROOT / "artifacts/phase_02"
    output.mkdir(parents=True, exist_ok=True)
    (output / "acceptance.json").unlink(missing_ok=True)
    if args.download_source:
        from phase_01_acceptance import acquire_source

        acquire_source(ROOT / "data/raw")
    result = run_from_root(ROOT)
    expected = {"dummy_prior", "logistic", "logistic_balanced", "logistic_smote"}
    if not expected <= {r["model_name"] for r in result["runs"]}:
        raise ValueError("Missing required supervised/SMOTE candidate")
    if len([r for r in result["runs"] if r["kind"] == "xgboost"]) != 6:
        raise ValueError("The reviewed acceptance grid requires six XGBoost candidates")
    if any(r["test_opened"] or r["fit_source"] != "train" or r["evaluation_source"] != "validation"
           for r in result["runs"]):
        raise ValueError("Experiment source boundary violation")
    notebooks = []
    if args.execute_notebooks:
        for directory in (ROOT, ROOT / "notebooks"):
            for notebook in sorted((ROOT / "notebooks").glob("0[2-5]_*.ipynb")):
                document = nbformat.read(notebook, as_version=4)
                NotebookClient(document, timeout=600, kernel_name="python3",
                    resources={"metadata": {"path": str(directory)}}).execute()
                name = notebook.stem + (".from-root" if directory == ROOT else ".from-notebooks")
                save_executed_notebook(document, output / "notebooks" / (name + ".ipynb"))
                notebooks.append(name)
        if len(notebooks) != 8:
            raise ValueError("Expected four Phase 2 notebooks in both working directories")
    evidence = {"technical_pipeline_passed": True,
        "accepted": False, "research_acceptance": "pending_two_independent_reviewers",
        "test_opened": False, "candidate": result["candidate"],
        "source_kind": result["source_kind"], "split_sha256": result["split_sha256"],
        "reference_protocol_executed": True, "candidate_runs_per_protocol": len(result["runs"]),
        "notebooks_executed": notebooks, "notebook_gate_passed": len(notebooks) == 8,
        "config": load_config(ROOT), **code_revision(ROOT),
        "run_url": os.environ.get("GITHUB_SERVER_URL", "https://github.com") + "/"
        + os.environ.get("GITHUB_REPOSITORY", "ManhT005/credit-card-fraud-bigdata")
        + "/actions/runs/" + os.environ.get("GITHUB_RUN_ID", "local")}
    write_json(output / "acceptance.json", evidence)
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
