import json

import pytest

from fraud_detection.ingestion.profiling import sha256_file
from fraud_detection.preprocessing.manifest import verified_intake


def test_source_sha_mismatch_stops_before_any_training(fraud_frame, tmp_path):
    csv = tmp_path / "creditcard.csv"
    fraud_frame.to_csv(csv, index=False)
    digest = sha256_file(csv)
    (tmp_path / "acceptance.json").write_text(json.dumps({"accepted": True, "csv_sha256": digest}))
    (tmp_path / "dataset_manifest.json").write_text(json.dumps({"local_sha256": digest}))
    (tmp_path / "source_provenance.json").write_text(json.dumps({
        "csv_sha256": "wrong", "source_metadata": {"id": "1597", "version": "1"}}))
    with pytest.raises(ValueError, match="integrity mismatch"):
        verified_intake(csv, tmp_path)


def test_missing_phase1_evidence_fails_closed(fraud_frame, tmp_path):
    csv = tmp_path / "creditcard.csv"
    fraud_frame.to_csv(csv, index=False)
    with pytest.raises(FileNotFoundError):
        verified_intake(csv, tmp_path)
