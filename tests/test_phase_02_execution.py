"""Offline notebook regression; original-source acceptance is a separate hosted job."""

import importlib.util
import json
import shutil
from pathlib import Path

import nbformat
import pytest
from nbclient import NotebookClient

from fraud_detection.models.baselines import baseline_specs
from fraud_detection.pipelines.train import (
    code_revision,
    load_config,
    load_verified_results,
    prepare_splits,
    run_experiment,
)
from fraud_detection.preprocessing.manifest import write_json

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def synthetic_notebook_root(fraud_frame, tmp_path):
    (tmp_path / "src/fraud_detection").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("# notebook test checkout\n")
    shutil.copytree(ROOT / "configs", tmp_path / "configs")
    shutil.copytree(ROOT / "notebooks", tmp_path / "notebooks")
    (tmp_path / "data/raw").mkdir(parents=True)
    csv = tmp_path / "data/raw/creditcard.csv"
    fraud_frame.to_csv(csv, index=False)
    from fraud_detection.ingestion.profiling import sha256_file

    intake = {"source_kind": "synthetic_fixture", "original_csv_sha256": sha256_file(csv)}
    output = tmp_path / "artifacts/phase_02"
    config = load_config(tmp_path)
    split, manifest, ref, ref_manifest = prepare_splits(fraud_frame, intake, config, output)
    revision = code_revision(tmp_path)
    specs = baseline_specs()[:3]
    result = run_experiment(fraud_frame, split, manifest, config, output, revision, specs=specs)
    reference = run_experiment(fraud_frame, ref, ref_manifest, config,
                               output / "reference", revision, specs=specs)
    result["reference_candidate"] = reference["candidate"]
    write_json(output / "experiment.json", result)
    return tmp_path


@pytest.mark.notebook
@pytest.mark.parametrize("directory", [".", "notebooks"])
def test_all_phase2_notebooks_execute_without_raw_output(synthetic_notebook_root, directory,
                                                        monkeypatch):
    root = synthetic_notebook_root
    monkeypatch.setenv("MPLBACKEND", "Agg")
    for path in sorted((root / "notebooks").glob("0[2-5]_*.ipynb")):
        notebook = nbformat.read(path, as_version=4)
        NotebookClient(notebook, timeout=120, kernel_name="python3",
                        resources={"metadata": {"path": str(root / directory)}}).execute()
        assert all(c.execution_count is not None for c in notebook.cells if c.cell_type == "code")
        for cell in notebook.cells:
            assert "df.head(" not in cell.source and "test_metrics" not in cell.source


def test_stale_notebook_artifacts_rejected(synthetic_notebook_root):
    root = synthetic_notebook_root
    assert load_verified_results(root)["source_kind"] == "synthetic_fixture"
    config = root / "configs/phase_02_models.yaml"
    config.write_text(config.read_text().replace("threads: 2", "threads: 1"))
    with pytest.raises(ValueError, match="Stale experiment"):
        load_verified_results(root)


def test_aggregate_artifacts_have_no_test_metrics(synthetic_notebook_root):
    path = synthetic_notebook_root / "artifacts/phase_02/experiment.json"
    result = json.loads(path.read_text())
    assert result["test_opened"] is False
    assert all(run["evaluation_source"] == "validation" for run in result["runs"])
    assert all("test_metrics" not in run and "predictions" not in run for run in result["runs"])


def test_acceptance_saves_notebook_in_a_clean_output_directory(tmp_path):
    path = ROOT / "scripts/phase_02_acceptance.py"
    spec = importlib.util.spec_from_file_location("phase_02_acceptance", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    document = nbformat.v4.new_notebook(cells=[nbformat.v4.new_markdown_cell("Aggregate evidence")])
    destination = tmp_path / "missing/phase_02/notebooks/executed.ipynb"
    module.save_executed_notebook(document, destination)
    assert nbformat.read(destination, as_version=4).cells[0].source == "Aggregate evidence"
