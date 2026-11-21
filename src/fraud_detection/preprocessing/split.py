"""Deterministic row partitioning with full-record leakage guards."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from fraud_detection.ingestion.profiling import EXPECTED_COLUMNS, FEATURE_COLUMNS


class SplitContractError(ValueError):
    """A partition would violate the frozen experiment protocol."""


def fingerprints(frame: pd.DataFrame, *, features_only: bool = False) -> np.ndarray:
    """Hash canonical numeric records, including Time and (by default) the label."""
    columns = FEATURE_COLUMNS if features_only else EXPECTED_COLUMNS
    values = frame.loc[:, list(columns)].to_numpy(dtype="<f8", copy=True)
    if not np.isfinite(values).all():
        raise SplitContractError("Split inputs must be finite numeric source values")
    values[values == 0] = 0  # Normalize signed zero, consistent with numeric equality.
    return np.array([hashlib.sha256(row.tobytes()).hexdigest() for row in values])


@dataclass(frozen=True)
class SplitIndices:
    train: np.ndarray
    validation: np.ndarray
    test: np.ndarray
    strategy: str

    def __post_init__(self):
        for part in (self.train, self.validation, self.test):
            part.setflags(write=False)


def audit_split(frame: pd.DataFrame, split: SplitIndices) -> dict:
    """Audit IDs, class coverage and exact records without exporting row identities."""
    parts = {name: getattr(split, name) for name in ("train", "validation", "test")}
    ids = np.concatenate(list(parts.values()))
    if len(ids) != len(frame) or not np.array_equal(np.sort(ids), np.arange(len(frame))):
        raise SplitContractError("Partitions must cover every row exactly once")
    record_hashes = fingerprints(frame)
    sets = {key: set(record_hashes[idx]) for key, idx in parts.items()}
    for a, b in (("train", "validation"), ("train", "test"), ("validation", "test")):
        if sets[a] & sets[b]:
            raise SplitContractError(f"Exact-record leakage between {a} and {b}")
    summary = {}
    for name, idx in parts.items():
        subset = frame.iloc[idx]
        counts = subset["Class"].value_counts()
        if set(counts.index) != {0, 1}:
            raise SplitContractError(f"{name} must contain both binary classes")
        summary[name] = {
            "rows": len(idx), "class_counts": {str(c): int(counts[c]) for c in (0, 1)},
            "fraud_rate": float(counts[1] / len(idx)),
            "time_min": float(subset.Time.min()), "time_max": float(subset.Time.max()),
            "index_sha256": hashlib.sha256(idx.astype("<i8").tobytes()).hexdigest(),
        }
    if split.strategy == "chronological":
        if not (summary["train"]["time_max"] < summary["validation"]["time_min"]
                <= summary["validation"]["time_max"] < summary["test"]["time_min"]):
            raise SplitContractError("Time groups must be strictly separated across cuts")
        if any(not frame.iloc[idx].Time.is_monotonic_increasing for idx in parts.values()):
            raise SplitContractError("Chronological partitions must be time ordered")
    feature_hash = fingerprints(frame, features_only=True)
    conflicts = pd.DataFrame({"hash": feature_hash, "label": frame.Class.to_numpy()})
    conflict_count = int((conflicts.groupby("hash").label.nunique() > 1).sum())
    return {"strategy": split.strategy, "partitions": summary,
            "row_id_overlap": 0, "exact_record_overlap": 0,
            "source_duplicate_rows": int(frame.duplicated().sum()),
            "conflicting_feature_groups": conflict_count,
            "duplicate_policy": "retain; keep full-record groups together"}


def chronological_split(frame: pd.DataFrame, train_fraction: float = .7,
                        validation_fraction: float = .15) -> SplitIndices:
    """Pick nearest nonempty Time-group boundaries; never split equal timestamps."""
    if not (0 < train_fraction < 1 and 0 < validation_fraction < 1
            and train_fraction + validation_fraction < 1):
        raise SplitContractError("Invalid chronological fractions")
    fingerprints(frame)  # Validate before sorting, including labels and every feature.
    order = np.lexsort((np.arange(len(frame)), frame.Time.to_numpy()))
    times = frame.iloc[order].Time.to_numpy()
    boundaries = np.flatnonzero(times[1:] != times[:-1]) + 1
    if len(boundaries) < 2:
        raise SplitContractError("Need at least three distinct Time groups")
    first = int(boundaries[:-1][np.argmin(abs(boundaries[:-1] - len(frame)*train_fraction))])
    later = boundaries[boundaries > first]
    second = int(later[np.argmin(abs(later - len(frame)*(train_fraction+validation_fraction)))])
    split = SplitIndices(order[:first], order[first:second], order[second:], "chronological")
    audit_split(frame, split)
    return split


def stratified_reference_split(frame: pd.DataFrame, seed: int = 42,
                               train_fraction: float = .6,
                               validation_fraction: float = .2) -> SplitIndices:
    """Stratify unique exact-record groups; retain duplicates within their partition.

    Fractions apply to groups, so row fractions/prevalence are approximate and audited.
    This protocol is independent of the chronological primary experiment.
    """
    if not (0 < train_fraction < 1 and 0 < validation_fraction < 1
            and train_fraction + validation_fraction < 1):
        raise SplitContractError("Invalid reference fractions")
    hashes = fingerprints(frame)
    unique, first, inverse = np.unique(hashes, return_index=True, return_inverse=True)
    labels = frame.Class.to_numpy()[first]
    try:
        train_val, test = train_test_split(np.arange(len(unique)),
            test_size=1-train_fraction-validation_fraction, stratify=labels, random_state=seed)
        train, val = train_test_split(train_val,
            test_size=validation_fraction/(train_fraction+validation_fraction),
            stratify=labels[train_val], random_state=seed)
    except ValueError as exc:
        raise SplitContractError(f"Not enough class groups for reference split: {exc}") from exc
    indices = [np.flatnonzero(np.isin(inverse, groups)) for groups in (train, val, test)]
    split = SplitIndices(*indices, "grouped_stratified_random")
    audit_split(frame, split)
    return split
