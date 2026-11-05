"""Exercise the actual notebook from both supported working directories."""

import shutil
from pathlib import Path

import nbformat
import pandas as pd
import pytest
from nbclient import NotebookClient

from fraud_detection.ingestion.profiling import EXPECTED_COLUMNS
from fraud_detection.paths import find_project_root

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("directory", [".", "notebooks"])
def test_notebook_executes_from_supported_directories(tmp_path, monkeypatch, directory):
    monkeypatch.setenv("MPLBACKEND", "Agg")
    (tmp_path / "src/fraud_detection").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("# isolated checkout marker\n")
    (tmp_path / "data/raw").mkdir(parents=True)
    (tmp_path / "notebooks").mkdir()
    rows = [{**{c: float(i + 1) for c in EXPECTED_COLUMNS}, "Class": i % 2}
            for i in range(8)]
    pd.DataFrame(rows).to_csv(tmp_path / "data/raw/creditcard.csv", index=False)
    notebook_path = tmp_path / "notebooks/01_data_profiling.ipynb"
    shutil.copyfile(ROOT / "notebooks/01_data_profiling.ipynb", notebook_path)
    notebook = nbformat.read(notebook_path, as_version=4)
    NotebookClient(notebook, timeout=120, kernel_name="python3",
                   resources={"metadata": {"path": str(tmp_path / directory)}}).execute()
    assert (tmp_path / "artifacts/phase_01/profile.json").is_file()
    assert not (tmp_path / "notebooks/artifacts").exists()
    for cell in notebook.cells:
        if cell.cell_type == "code":
            assert cell.execution_count is not None
            assert not any(item.output_type == "error" for item in cell.outputs)


def test_project_root_rejects_unrelated_directory(tmp_path):
    with pytest.raises(FileNotFoundError, match="checkout"):
        find_project_root(tmp_path)
