"""Validation-only operating-point selection; no test-opening API."""

import numpy as np
from sklearn.metrics import precision_recall_curve

from fraud_detection.evaluation.metrics import (
    binary_metrics,
    require_validation,
    validate_scores,
)


def select_threshold(y, scores, *, source: str = "validation") -> dict:
    """Maximize exact validation F2, breaking ties toward the highest threshold."""
    require_validation(source)
    y, scores = validate_scores(y, scores)
    precision, recall, thresholds = precision_recall_curve(y, scores)
    denominator = 4*precision[:-1] + recall[:-1]
    f2 = np.divide(5*precision[:-1]*recall[:-1], denominator,
                   out=np.zeros_like(denominator), where=denominator != 0)
    best = np.flatnonzero(f2 == f2.max())[-1]
    threshold = float(thresholds[best])
    return {"threshold": threshold, "objective": "validation_f2",
            "selected_on": source, "tie_policy": "highest threshold among equal maxima",
            "metrics": binary_metrics(y, scores, threshold, source=source)}


def threshold_summary(y, scores) -> list[dict]:
    """A bounded aggregate operating-point table for inspection, not retuning test."""
    y, scores = validate_scores(y, scores)
    return [binary_metrics(y, scores, float(t))
            for t in np.unique(np.quantile(scores, np.linspace(0, 1, 21)))]
