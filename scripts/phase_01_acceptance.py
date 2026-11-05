"""Verify the pinned OpenML source, profile it, and execute the Phase 1 notebook.

Run after installing .[data,notebook,dev]. Downloads stay in ignored data/raw;
only aggregate reports and the notebook without raw row previews are published.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import nbformat
import pandas as pd
from nbclient import NotebookClient
from scipy.io import arff

from fraud_detection.ingestion.profiling import (
    EXPECTED_COLUMNS,
    EXPECTED_ORIGINAL_FRAUD,
    EXPECTED_ORIGINAL_ROWS,
    run_profile,
    sha256_file,
)

ROOT = Path(__file__).resolve().parents[1]
METADATA_URL = "https://www.openml.org/api/v1/json/data/1597"
PINNED_MD5 = "178bcf9bb1f31a3dfe12d0e577884add"
SOURCE_URL = "https://www.openml.org/data/v1/download/1673544/creditcard.arff"


def fetch(url: str):
    """Use public, credential-free source endpoints with an explicit timeout."""
    try:
        return urlopen(Request(url, headers={"User-Agent": "fraud-bigdata-phase1/0.1"}),
                       timeout=60)
    except (HTTPError, URLError):
        # OpenML also exposes official API download routes on api.openml.org.
        fallback = url.replace("www.openml.org", "api.openml.org")
        return urlopen(Request(fallback, headers={"User-Agent": "fraud-bigdata-phase1/0.1"}),
                       timeout=60)


def acquire_source(raw: Path) -> tuple[Path, dict]:
    """Download exact source bytes; preserve Time when exporting ARFF to CSV."""
    raw.mkdir(parents=True, exist_ok=True)
    with fetch(METADATA_URL) as response:
        metadata = json.load(response)["data_set_description"]
    expected = {"id": "1597", "version": "1", "file_id": "1673544",
                "md5_checksum": PINNED_MD5, "licence": "Public"}
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise ValueError(f"Source metadata changed: {key}={metadata.get(key)!r}")
    source = raw / "creditcard.arff"
    partial = raw / "creditcard.arff.part"
    with fetch(SOURCE_URL) as response, partial.open("wb") as stream:
        download_url = response.geturl()
        shutil.copyfileobj(response, stream)
    digest = hashlib.md5(usedforsecurity=False)
    with partial.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != PINNED_MD5:
        raise ValueError("Downloaded ARFF does not match the OpenML source MD5")
    partial.replace(source)
    records, _ = arff.loadarff(source)
    frame = pd.DataFrame(records)
    if tuple(frame.columns) != EXPECTED_COLUMNS:
        raise ValueError(f"Source schema mismatch: {list(frame.columns)}")
    # ARFF nominal labels are bytes; convert representation only, without filtering.
    frame["Class"] = pd.to_numeric(frame["Class"], errors="raise").astype("int64")
    csv = raw / "creditcard.csv"
    frame.to_csv(csv, index=False, float_format="%.17g")
    selected = {key: metadata.get(key) for key in (
        "id", "name", "version", "version_label", "file_id", "format", "licence",
        "url", "upload_date", "default_target_attribute", "row_id_attribute",
        "md5_checksum", "creator",
    )}
    return csv, {
        "metadata_url": METADATA_URL,
        "source_metadata": selected,
        "download_url": download_url,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_arff_md5": digest.hexdigest(),
        "source_arff_sha256": sha256_file(source),
        "csv_sha256": sha256_file(csv),
        "conversion": "ARFF to CSV; all columns and rows retained; nominal Class to integer",
        "license_review": (
            "OpenML declares 'Public', not a specific SPDX license. This records the source "
            "declaration only; no MIT or commercial-redistribution permission is inferred. "
            "Source transactions are not redistributed by this repository."
        ),
    }


def main() -> None:
    output = ROOT / "artifacts/phase_01"
    output.mkdir(parents=True, exist_ok=True)
    # A failed rerun must never leave a stale successful acceptance marker.
    (output / "acceptance.json").unlink(missing_ok=True)
    csv, acquisition = acquire_source(ROOT / "data/raw")
    (output / "source_provenance.json").write_text(
        json.dumps(acquisition, indent=2) + "\n", encoding="utf-8"
    )
    profile = run_profile(csv, output)
    if (not profile["valid"] or profile["rows"] != EXPECTED_ORIGINAL_ROWS
            or profile["class_counts"]["1"] != EXPECTED_ORIGINAL_FRAUD):
        raise ValueError("Original-data validation failed; inspect profile.json")
    unexpected = [item for item in profile["findings"] if item["code"] != "DUPLICATE_ROWS"]
    if unexpected:
        raise ValueError(f"Unreviewed source-quality findings: {unexpected}")
    notebook = nbformat.read(ROOT / "notebooks/01_data_profiling.ipynb", as_version=4)
    NotebookClient(
        notebook, timeout=600, kernel_name="python3",
        resources={"metadata": {"path": str(ROOT / "notebooks")}},
    ).execute()
    nbformat.write(notebook, output / "01_data_profiling.executed.ipynb")
    evidence = {
        "accepted": True,
        "source_revision": os.environ.get("GITHUB_SHA", "local checkout"),
        "pr_head_sha": os.environ.get("PR_HEAD_SHA", "local checkout"),
        "run_url": os.environ.get("GITHUB_SERVER_URL", "https://github.com") + "/"
        + os.environ.get("GITHUB_REPOSITORY", "ManhT005/credit-card-fraud-bigdata")
        + "/actions/runs/" + os.environ.get("GITHUB_RUN_ID", "local"),
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "rows": profile["rows"], "class_counts": profile["class_counts"],
        "fraud_rate": profile["fraud_rate"],
        "duplicate_rows": profile["duplicate_rows"],
        "duplicates_by_class": profile["duplicates_by_class"],
        "findings": profile["findings"],
        "source_arff_sha256": acquisition["source_arff_sha256"],
        "csv_sha256": acquisition["csv_sha256"],
        "notebook_executed_from": "notebooks/ (all code cells)",
        "quality_review": "Duplicates retained; missing/invalid findings reviewed below",
        "phase_2_risks_reviewed": [
            "Split before learned preprocessing; SMOTE on training folds only",
            "Guard exact duplicate overlap across splits without automatic row deletion",
            "Tune thresholds on validation; protect held-out test",
            "Two-day Time window is not evidence of long-term temporal robustness",
            "Original PCA fit is not auditable from anonymized components",
        ],
        "license_review": acquisition["license_review"],
        "versions": {name: version(name) for name in ("pandas", "numpy", "nbclient", "scipy")},
    }
    (output / "acceptance.json").write_text(
        json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
