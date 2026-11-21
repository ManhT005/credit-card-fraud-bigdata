"""Reproducible supervised baselines with train-derived class balancing."""

from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression


def baseline_specs() -> list[dict]:
    return [{"name": "dummy_prior", "kind": "dummy", "balance": "none"},
            {"name": "logistic", "kind": "logistic", "balance": "none"},
            {"name": "logistic_balanced", "kind": "logistic", "balance": "class_weight"},
            {"name": "logistic_smote", "kind": "logistic", "balance": "smote"}]


def baseline_estimator(spec: dict, seed: int):
    if spec["kind"] == "dummy":
        return DummyClassifier(strategy="prior", random_state=seed)
    return LogisticRegression(C=1.0, max_iter=2000, random_state=seed,
                              class_weight="balanced" if spec["balance"] == "class_weight"
                              else None)
