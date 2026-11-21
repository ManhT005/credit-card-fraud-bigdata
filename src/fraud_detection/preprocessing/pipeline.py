"""Allowlisted features; learned transforms and optional SMOTE fit only within fit()."""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from fraud_detection.ingestion.profiling import FEATURE_COLUMNS


def select_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Prevent target, source row position and split metadata from reaching a learner."""
    missing = set(FEATURE_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing features: {sorted(missing)}")
    return frame.loc[:, list(FEATURE_COLUMNS)].copy()


def class_counts(y) -> dict:
    values, counts = np.unique(y, return_counts=True)
    return {str(int(value)): int(n) for value, n in zip(values, counts)}


def build_pipeline(estimator, *, smote: bool = False, seed: int = 42,
                   k_neighbors: int = 5, sampling_strategy: float = .1,
                   impute: bool = False):
    steps = []
    if impute:
        steps.append(("imputer", SimpleImputer(strategy="median")))
    steps.append(("scaler", StandardScaler()))
    features = ColumnTransformer([("features", Pipeline(steps), list(FEATURE_COLUMNS))],
                                 remainder="drop")
    if smote:
        from imblearn.over_sampling import SMOTE
        from imblearn.pipeline import Pipeline as ImbalancedPipeline

        class AuditedSMOTE(SMOTE):
            def fit_resample(self, X, y, **params):
                self.input_class_counts_ = class_counts(y)
                result = super().fit_resample(X, y, **params)
                self.output_class_counts_ = class_counts(result[1])
                return result

        sampler = AuditedSMOTE(random_state=seed, k_neighbors=k_neighbors,
                               sampling_strategy=sampling_strategy)
        return ImbalancedPipeline([("features", features), ("smote", sampler),
                                   ("estimator", estimator)])
    return Pipeline([("features", features), ("estimator", estimator)])
