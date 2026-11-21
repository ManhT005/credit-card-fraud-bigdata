import numpy as np
from sklearn.linear_model import LogisticRegression

from fraud_detection.ingestion.profiling import FEATURE_COLUMNS
from fraud_detection.preprocessing.pipeline import build_pipeline, select_features


def test_validation_extremes_do_not_change_fitted_scaler(fraud_frame):
    raw = fraud_frame.copy(deep=True)
    train = select_features(fraud_frame.iloc[:160])
    val = select_features(fraud_frame.iloc[160:])
    val.loc[:, "Amount"] = 1e12
    pipeline = build_pipeline(LogisticRegression(max_iter=1000))
    pipeline.fit(train, fraud_frame.Class.iloc[:160])
    scaler = pipeline.named_steps["features"].named_transformers_["features"].named_steps["scaler"]
    before = scaler.mean_.copy()
    pipeline.predict_proba(val)
    np.testing.assert_allclose(before, train.mean().to_numpy())
    np.testing.assert_array_equal(scaler.mean_, before)
    assert scaler.n_samples_seen_ == len(train)
    assert fraud_frame.equals(raw)


def test_target_and_audit_fields_excluded(fraud_frame):
    fraud_frame["row_id"] = range(len(fraud_frame))
    fraud_frame["split"] = "train"
    X = select_features(fraud_frame)
    assert tuple(X.columns) == FEATURE_COLUMNS
    assert "Class" not in X and "row_id" not in X and "split" not in X
