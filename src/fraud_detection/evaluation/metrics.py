"""Binary fraud metrics with explicit score, label and undefined-metric contracts."""

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    fbeta_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


def validate_scores(y, scores):
    y, scores = np.asarray(y), np.asarray(scores, dtype=float)
    if y.ndim != 1 or scores.ndim != 1 or y.shape != scores.shape or not len(y):
        raise ValueError("Labels and scores must be nonempty aligned 1-D arrays")
    if set(np.unique(y)) != {0, 1}:
        raise ValueError("AP/ROC evaluation requires both binary classes")
    if not np.isfinite(scores).all():
        raise ValueError("Risk scores must be finite")
    return y.astype(int), scores


def require_validation(source: str) -> None:
    if source != "validation":
        raise ValueError("Phase 2 selection/evaluation accepts validation only; test is sealed")


def binary_metrics(y, scores, threshold: float, *, source: str = "validation",
                   k: int = 100) -> dict:
    require_validation(source)
    y, scores = validate_scores(y, scores)
    if not np.isfinite(threshold) or not isinstance(k, int) or k < 1:
        raise ValueError("Threshold must be finite and k a positive integer")
    predicted = (scores >= threshold).astype(int)
    tn, fp, fn, tp = map(int, confusion_matrix(y, predicted, labels=[0, 1]).ravel())
    top = np.argsort(-scores, kind="stable")[:min(k, len(y))]
    return {
        "average_precision": float(average_precision_score(y, scores)),
        "roc_auc": float(roc_auc_score(y, scores)),
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "f1": float(fbeta_score(y, predicted, beta=1, zero_division=0)),
        "f2": float(fbeta_score(y, predicted, beta=2, zero_division=0)),
        "confusion_matrix": [[tn, fp], [fn, tp]],
        "tn": tn, "fp": fp, "fn": fn, "tp": tp,
        "alerts": tp+fp, "alert_rate": float((tp+fp)/len(y)),
        "alerts_per_1000": float(1000*(tp+fp)/len(y)),
        "precision_at_k": float(y[top].mean()), "k": len(top),
        "ranking_tie_policy": "stable validation row order; ties are not calibrated ranking",
        "threshold": float(threshold), "evaluation_source": source,
        "zero_division": 0,
    }


def aggregate_curves(y, scores, points: int = 150) -> dict:
    """Thin plot coordinates; do not export per-row scores or predictions."""
    y, scores = validate_scores(y, scores)
    precision, recall, _ = precision_recall_curve(y, scores)
    fpr, tpr, _ = roc_curve(y, scores)
    pr_idx = np.unique(np.linspace(0, len(precision)-1, min(points, len(precision))).astype(int))
    roc_idx = np.unique(np.linspace(0, len(tpr)-1, min(points, len(tpr))).astype(int))
    return {"precision": precision[pr_idx].tolist(), "recall": recall[pr_idx].tolist(),
            "fpr": fpr[roc_idx].tolist(), "tpr": tpr[roc_idx].tolist()}
