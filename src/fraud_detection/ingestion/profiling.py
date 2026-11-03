"""Read-only Phase 1 profiling for the original OpenML 1597 credit-card dataset.

No split, resampling, imputation, scaling, or row deletion is performed here.
The output describes the *local input*, not an independently verified OpenML version.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

FEATURE_COLUMNS = ("Time", *(f"V{i}" for i in range(1, 29)), "Amount")
EXPECTED_COLUMNS = (*FEATURE_COLUMNS, "Class")
SOURCE_URL = "https://www.openml.org/d/1597"
EXPECTED_ORIGINAL_ROWS = 284_807
EXPECTED_ORIGINAL_FRAUD = 492


def sha256_file(path: str | Path) -> str:
    """Hash a file in chunks; never load the raw bytes into a report."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _numeric_summary(series: pd.Series) -> dict[str, float | None]:
    """Return JSON-safe descriptive statistics without altering the input."""
    values = pd.to_numeric(series, errors="coerce")
    values = values.where(values.notna() & (values.abs() != float("inf")))
    result = values.describe(percentiles=[0.25, 0.5, 0.75, 0.95, 0.99])
    return {
        name: (None if pd.isna(result.get(key)) else float(result[key]))
        for name, key in (
            ("mean", "mean"),
            ("std", "std"),
            ("min", "min"),
            ("q25", "25%"),
            ("median", "50%"),
            ("q75", "75%"),
            ("p95", "95%"),
            ("p99", "99%"),
            ("max", "max"),
        )
    }


def profile_dataframe(df: pd.DataFrame, *, check_reference: bool = True) -> dict:
    """Inspect schema, missingness, invalid values, duplicates and class balance.

    Raises for missing/extra columns because a different schema cannot be profiled
    as OpenML 1597. Data-quality findings are *reported*, never silently repaired.
    """
    if df.columns.duplicated().any():
        raise ValueError("Duplicate column names are not allowed")
    missing_columns = sorted(set(EXPECTED_COLUMNS) - set(df.columns))
    extra_columns = sorted(set(df.columns) - set(EXPECTED_COLUMNS))
    if missing_columns or extra_columns:
        raise ValueError(
            f"Unexpected schema: missing={missing_columns}, extra={extra_columns}"
        )

    findings: list[dict] = []

    def add(code: str, severity: str, count: int, explanation: str) -> None:
        if count:
            findings.append({
                "code": code,
                "severity": severity,
                "count": int(count),
                "description": explanation,
            })

    add("EMPTY_DATASET", "error", int(df.empty), "No rows to profile")
    missing = {col: int(df[col].isna().sum()) for col in EXPECTED_COLUMNS}
    add("MISSING_TARGET", "error", missing["Class"], "Class label must be present")
    add("MISSING_FEATURE", "warning", sum(missing[col] for col in FEATURE_COLUMNS),
        "Missing features need review; no imputation was applied")

    non_numeric: dict[str, int] = {}
    non_finite: dict[str, int] = {}
    for col in EXPECTED_COLUMNS:
        values = pd.to_numeric(df[col], errors="coerce")
        bad = int((values.isna() & df[col].notna()).sum())
        infinite = int(values.isin([float("inf"), float("-inf")]).sum())
        non_numeric[col] = bad
        non_finite[col] = infinite
        add("NON_NUMERIC_" + col, "error", bad, f"{col} contains non-numeric data")
        add("NON_FINITE_" + col, "error", infinite, f"{col} contains infinities")

    target = pd.to_numeric(df["Class"], errors="coerce")
    invalid_target = int((target.notna() & ~target.isin([0, 1])).sum())
    add("INVALID_TARGET", "error", invalid_target, "Class must be 0 or 1")

    for col in ("Time", "Amount"):
        vals = pd.to_numeric(df[col], errors="coerce")
        add("NEGATIVE_" + col.upper(), "error", int((vals < 0).sum()),
            f"{col} cannot be negative")

    exact_duplicates = df.duplicated(keep="first")
    duplicate_count = int(exact_duplicates.sum())
    add("DUPLICATE_ROWS", "warning", duplicate_count,
        "Exact duplicate rows are retained; deletion needs explicit policy")

    valid_target = target[target.isin([0, 1])]
    class_counts = {str(label): int((valid_target == label).sum()) for label in (0, 1)}
    if check_reference:
        add("REFERENCE_ROW_COUNT_MISMATCH", "warning",
            int(len(df) != EXPECTED_ORIGINAL_ROWS),
            "Local input differs from the documented original row count")
        add("REFERENCE_FRAUD_COUNT_MISMATCH", "warning",
            int(class_counts["1"] != EXPECTED_ORIGINAL_FRAUD),
            "Local input differs from the documented original fraud count")

    summary = {
        "schema": {
            "columns": len(df.columns),
            "features": len(FEATURE_COLUMNS),
            "names": list(EXPECTED_COLUMNS),
            "dtypes": {c: str(df[c].dtype) for c in EXPECTED_COLUMNS},
        },
        "rows": len(df),
        "null_count": missing,
        "non_numeric_count": non_numeric,
        "non_finite_count": non_finite,
        "duplicate_rows": duplicate_count,
        "duplicates_by_class": {
            str(label): int((exact_duplicates & (target == label)).sum())
            for label in (0, 1)
        },
        "class_counts": class_counts,
        "fraud_rate": float(class_counts["1"] / len(df)) if len(df) else None,
        "statistics": {
            col: _numeric_summary(df[col]) for col in ("Time", "Amount")
        },
        "per_class_amount": {
            str(label): _numeric_summary(df.loc[target == label, "Amount"])
            for label in (0, 1)
        },
        "findings": findings,
        "valid": not any(item["severity"] == "error" for item in findings),
        "scope": "read-only Phase 1 inspection; no transformations or ML",
    }
    return summary


def run_profile(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    check_reference: bool = True,
) -> dict:
    """Profile local CSV and write non-sensitive JSON/CSV summaries."""
    path = Path(input_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(
            f"Dataset not found: {path}. Put creditcard.csv in data/raw/."
        )
    df = pd.read_csv(path)
    profile = profile_dataframe(df, check_reference=check_reference)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    column_profile = pd.DataFrame({
        "column": list(EXPECTED_COLUMNS),
        "dtype": [str(df[c].dtype) for c in EXPECTED_COLUMNS],
        "null_count": [profile["null_count"][c] for c in EXPECTED_COLUMNS],
        "non_numeric_count": [
            profile["non_numeric_count"][c] for c in EXPECTED_COLUMNS
        ],
        "unique_count": [int(df[c].nunique(dropna=True)) for c in EXPECTED_COLUMNS],
    })
    column_profile.to_csv(out / "column_profile.csv", index=False)
    (out / "profile.json").write_text(
        json.dumps(profile, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "source_attribution": {
            "provider": "OpenML",
            "dataset_id": 1597,
            "url": SOURCE_URL,
            "source_version": "not independently verified",
        },
        "local_file_name": path.name,
        "local_file_size_bytes": path.stat().st_size,
        "local_sha256": sha256_file(path),
        "profiled_at_utc": datetime.now(timezone.utc).isoformat(),
        "rows": profile["rows"],
        "class_counts": profile["class_counts"],
        "note": "Metadata describes the local file; not proof of source version.",
    }
    (out / "dataset_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return profile
