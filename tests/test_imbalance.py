import numpy as np
from sklearn.linear_model import LogisticRegression

from fraud_detection.models.candidates import candidate_estimator, risk_scores
from fraud_detection.preprocessing.pipeline import build_pipeline, select_features


def test_smote_resamples_training_only(fraud_frame):
    train, val = fraud_frame.iloc[:160], fraud_frame.iloc[160:]
    original = val.copy(deep=True)
    pipeline = build_pipeline(LogisticRegression(max_iter=1000), smote=True,
                               sampling_strategy=.5, k_neighbors=2)
    pipeline.fit(select_features(train), train.Class)
    sampler = pipeline.named_steps["smote"]
    before, after = sampler.input_class_counts_.copy(), sampler.output_class_counts_.copy()
    predicted = pipeline.predict_proba(select_features(val))
    assert sum(before.values()) == len(train) and sum(after.values()) > len(train)
    assert predicted.shape == (len(val), 2) and val.equals(original)
    assert sampler.input_class_counts_ == before and sampler.output_class_counts_ == after


def test_xgboost_weight_uses_only_training_labels():
    spec = {"kind": "xgboost", "parameters": {"n_estimators": 5, "max_depth": 2}}
    estimator = candidate_estimator(spec, [0, 0, 0, 1], 42)
    assert estimator.get_params()["scale_pos_weight"] == 3


def test_isolation_risk_direction():
    class Scorer:
        def score_samples(self, X):
            return np.array([-.1, -.9])

    np.testing.assert_array_equal(risk_scores(Scorer(), [0, 1], kind="isolation_forest"), [.1, .9])
