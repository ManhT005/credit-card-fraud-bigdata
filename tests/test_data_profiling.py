"""Phase 1 tests use a tiny synthetic fixture; no raw financial records in Git."""

import json

import pandas as pd
import pytest

from fraud_detection.ingestion.profiling import (
    FEATURE_COLUMNS,
    profile_dataframe,
    run_profile,
    sha256_file,
)


def sample_frame() -> pd.DataFrame:
    rows = []
    for fraud in (0, 1):
        item = {key: float(fraud + 1) for key in FEATURE_COLUMNS}
        item.update({"Time": float(fraud), "Amount": float(10 + fraud), "Class": fraud})
        rows.append(item)
    return pd.DataFrame(rows)


def test_clean_fixture_is_valid():
    profile = profile_dataframe(sample_frame(), check_reference=False)
    assert profile["valid"]
    assert profile["schema"]["columns"] == 31
    assert profile["class_counts"] == {"0": 1, "1": 1}
    assert profile["fraud_rate"] == 0.5
    assert profile["duplicate_rows"] == 0


def test_exact_duplicate_retained_as_warning():
    df = sample_frame()
    df = pd.concat([df, df.iloc[[1]]], ignore_index=True)
    report = profile_dataframe(df, check_reference=False)
    assert report["valid"]
    assert report["duplicate_rows"] == 1
    assert report["duplicates_by_class"]["1"] == 1
    assert any(x["code"] == "DUPLICATE_ROWS" for x in report["findings"])


def test_invalid_schema_rejected():
    with pytest.raises(ValueError, match="Unexpected schema"):
        profile_dataframe(sample_frame().drop(columns=["V28"]))


@pytest.mark.parametrize(
    ("column", "value", "code"),
    [
        ("Class", 2, "INVALID_TARGET"),
        ("Amount", -1, "NEGATIVE_AMOUNT"),
        ("V1", "bad", "NON_NUMERIC_V1"),
        ("Class", None, "MISSING_TARGET"),
    ],
)
def test_invalid_values_reported(column, value, code):
    df = sample_frame()
    df.loc[0, column] = value
    report = profile_dataframe(df, check_reference=False)
    assert not report["valid"]
    assert code in {finding["code"] for finding in report["findings"]}


def test_missing_feature_is_warning_only():
    df = sample_frame()
    df.loc[0, "V10"] = None
    report = profile_dataframe(df, check_reference=False)
    assert report["valid"]
    assert "MISSING_FEATURE" in {item["code"] for item in report["findings"]}


def test_outputs_and_provenance(tmp_path):
    source = tmp_path / "creditcard.csv"
    sample_frame().to_csv(source, index=False)
    out = tmp_path / "out"
    result = run_profile(source, out, check_reference=False)
    assert result["valid"]
    manifest = json.loads((out / "dataset_manifest.json").read_text())
    assert manifest["local_sha256"] == sha256_file(source)
    assert manifest["source_attribution"]["source_version"] == "not independently verified"
    assert json.loads((out / "profile.json").read_text())["rows"] == 2
    assert len(pd.read_csv(out / "column_profile.csv")) == 31


def test_file_missing(tmp_path):
    with pytest.raises(FileNotFoundError, match="Dataset not found"):
        run_profile(tmp_path / "missing.csv", tmp_path / "output")
