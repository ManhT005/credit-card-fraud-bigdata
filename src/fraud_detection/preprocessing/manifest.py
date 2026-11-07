"""Source intake and aggregate reproducibility metadata (no source rows)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from fraud_detection.ingestion.profiling import profile_dataframe, sha256_file
from fraud_detection.preprocessing.split import audit_split

PINNED_SOURCE_MD5 = "178bcf9bb1f31a3dfe12d0e577884add"


def digest_json(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def write_json(path: str | Path, value) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n",
                    encoding="utf-8")


def verified_intake(csv: str | Path, phase1_dir: str | Path) -> tuple[pd.DataFrame, dict]:
    """Require agreement with successful Phase 1 provenance, never just its row count."""
    csv, phase1_dir = Path(csv), Path(phase1_dir)
    evidence = json.loads((phase1_dir / "acceptance.json").read_text())
    provenance = json.loads((phase1_dir / "source_provenance.json").read_text())
    manifest = json.loads((phase1_dir / "dataset_manifest.json").read_text())
    sha = sha256_file(csv)
    metadata = provenance["source_metadata"]
    if not (evidence.get("accepted") is True
            and evidence.get("csv_sha256") == provenance.get("csv_sha256")
            == manifest.get("local_sha256") == sha
            and metadata.get("id") == "1597" and metadata.get("version") == "1"
            and metadata.get("file_id") == "1673544"
            and provenance.get("source_arff_md5") == metadata.get("md5_checksum")
            == PINNED_SOURCE_MD5
            and evidence.get("source_arff_sha256") == provenance.get("source_arff_sha256")):
        raise ValueError("Phase 1 source integrity mismatch; stop before splitting/training")
    frame = pd.read_csv(csv)
    profile = profile_dataframe(frame)
    unexpected = [f for f in profile["findings"] if f["code"] != "DUPLICATE_ROWS"]
    if (profile["rows"] != evidence.get("rows")
            or profile["class_counts"] != evidence.get("class_counts")):
        raise ValueError("Phase 1 evidence contradicts actual source row/class counts")
    if not profile["valid"] or unexpected:
        raise ValueError(f"Unexpected source-quality findings: {unexpected}")
    intake = {"source_kind": "verified_original", "original_csv_sha256": sha,
              "source_metadata": metadata, "phase1_evidence_sha256": digest_json(evidence),
              "rows": profile["rows"], "class_counts": profile["class_counts"],
              "duplicate_rows": profile["duplicate_rows"]}
    return frame, intake


def split_manifest(frame, split, intake: dict, config: dict) -> dict:
    manifest = {"dataset": intake, "audit": audit_split(frame, split),
                "config_sha256": digest_json(config), "seed": config["seed"],
                "test_opened": False}
    # Execution receipts have timestamps/run URLs. They must not change split identity.
    identity = {"original_csv_sha256": intake["original_csv_sha256"],
                "audit": manifest["audit"], "config_sha256": manifest["config_sha256"],
                "seed": config["seed"]}
    manifest["split_sha256"] = digest_json(identity)
    return manifest
