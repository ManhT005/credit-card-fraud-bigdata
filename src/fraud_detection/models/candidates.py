"""Bounded CPU candidates; positive weights derive from training labels only."""

import numpy as np
from sklearn.ensemble import IsolationForest


def candidate_estimator(spec: dict, y_train, seed: int, threads: int = 2):
    if spec["kind"] == "isolation_forest":
        return IsolationForest(n_estimators=100, random_state=seed, n_jobs=threads,
                               contamination="auto")
    from xgboost import XGBClassifier

    positives = int(np.sum(np.asarray(y_train) == 1))
    negatives = int(np.sum(np.asarray(y_train) == 0))
    if not positives or not negatives:
        raise ValueError("XGBoost requires both training classes")
    return XGBClassifier(objective="binary:logistic", eval_metric="logloss", tree_method="hist",
                         n_jobs=threads, random_state=seed, scale_pos_weight=negatives/positives,
                         learning_rate=.1, subsample=1.0, colsample_bytree=1.0,
                         **spec["parameters"])


def risk_scores(pipeline, X, *, kind: str):
    if kind == "isolation_forest":
        return -pipeline.score_samples(X)  # Larger anomaly => larger fraud risk.
    column = list(pipeline.classes_).index(1)
    return pipeline.predict_proba(X)[:, column]
