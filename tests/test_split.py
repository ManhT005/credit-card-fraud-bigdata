import numpy as np
import pandas as pd
import pytest

from fraud_detection.preprocessing.split import (
    SplitContractError,
    SplitIndices,
    audit_split,
    chronological_split,
    stratified_reference_split,
)


def test_chronological_replay_ties_and_row_integrity(fraud_frame):
    frame = fraud_frame.sample(frac=1, random_state=6).reset_index(drop=True)
    split = chronological_split(frame)
    again = chronological_split(frame)
    audit = audit_split(frame, split)
    assert sum(p["rows"] for p in audit["partitions"].values()) == len(frame)
    for name in ("train", "validation", "test"):
        assert np.array_equal(getattr(split, name), getattr(again, name))
        assert not getattr(split, name).flags.writeable
    partitions = [set(frame.iloc[getattr(split, n)].Time) for n in ("train", "validation", "test")]
    assert not partitions[0] & partitions[1] and not partitions[1] & partitions[2]
    assert audit["exact_record_overlap"] == 0


def test_duplicate_leakage_rejected(fraud_frame):
    frame = fraud_frame.copy()
    frame.iloc[180] = frame.iloc[0]
    split = SplitIndices(np.arange(160), np.arange(160, 200), np.arange(200, 240), "manual")
    with pytest.raises(SplitContractError, match="Exact-record leakage"):
        audit_split(frame, split)


def test_row_loss_and_id_overlap_rejected(fraud_frame):
    split = SplitIndices(np.arange(160), np.arange(159, 200), np.arange(201, 240), "manual")
    with pytest.raises(SplitContractError, match="exactly once"):
        audit_split(fraud_frame, split)


def test_reference_keeps_duplicate_groups_and_replays_seed(fraud_frame):
    frame = pd.concat([fraud_frame, fraud_frame.iloc[:12]], ignore_index=True)
    split = stratified_reference_split(frame, 42)
    again = stratified_reference_split(frame, 42)
    assert audit_split(frame, split)["exact_record_overlap"] == 0
    assert np.array_equal(split.train, again.train)
    assert not np.array_equal(split.train, stratified_reference_split(frame, 17).train)


@pytest.mark.parametrize("bad", ["single_class", "rare_class", "one_time", "non_finite"])
def test_invalid_split_fails_closed(fraud_frame, bad):
    frame = fraud_frame.copy()
    if bad == "single_class":
        frame["Class"] = 0
    elif bad == "rare_class":
        frame["Class"] = 0
        frame.loc[0, "Class"] = 1
    elif bad == "one_time":
        frame["Time"] = 0
    else:
        frame.loc[0, "V1"] = np.inf
    with pytest.raises(SplitContractError):
        chronological_split(frame)


def test_chronological_retains_duplicates_inside_time_groups(fraud_frame):
    frame = pd.concat([fraud_frame, fraud_frame.iloc[[0, 0, 100, 200]]], ignore_index=True)
    split = chronological_split(frame)
    assert audit_split(frame, split)["source_duplicate_rows"] == 4


def test_split_identity_is_independent_of_phase1_execution_receipt(fraud_frame):
    from fraud_detection.preprocessing.manifest import split_manifest

    split = chronological_split(fraud_frame)
    config = {"seed": 42}
    first = split_manifest(fraud_frame, split,
        {"original_csv_sha256": "same-file", "phase1_evidence_sha256": "run-a"}, config)
    second = split_manifest(fraud_frame, split,
        {"original_csv_sha256": "same-file", "phase1_evidence_sha256": "run-b"}, config)
    assert first["split_sha256"] == second["split_sha256"]
