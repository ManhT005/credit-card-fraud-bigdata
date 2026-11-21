import numpy as np
import pytest

from fraud_detection.evaluation.metrics import binary_metrics
from fraud_detection.evaluation.thresholds import select_threshold


def test_ap_and_confusion_match_hand_computed_fixture():
    # Sorted labels 1,0,1,0: AP=(1 + 2/3)/2=5/6, not trapezoidal PR area.
    y, scores = [1, 0, 1, 0], [.9, .8, .7, .1]
    metrics = binary_metrics(y, scores, .75, k=2)
    assert metrics["average_precision"] == pytest.approx(5/6)
    assert metrics["confusion_matrix"] == [[1, 1], [1, 1]]
    assert metrics["precision"] == metrics["recall"] == metrics["f1"] == metrics["f2"] == .5
    assert metrics["precision_at_k"] == .5
    policy = select_threshold(y, scores)
    assert policy["threshold"] == .7
    assert policy["metrics"]["f2"] == pytest.approx(10/11)


def test_constant_score_and_no_alerts_policy():
    y, scores = [0, 0, 1, 0], [.2]*4
    assert binary_metrics(y, scores, .5)["precision"] == 0
    assert binary_metrics(y, scores, .5)["average_precision"] == .25
    assert select_threshold(y, scores)["metrics"]["alerts"] == 4


@pytest.mark.parametrize("source", ["test", "train", "holdout"])
def test_selection_cannot_open_test_or_train(source):
    with pytest.raises(ValueError, match="validation only"):
        select_threshold([0, 1], [.1, .9], source=source)
    with pytest.raises(ValueError, match="validation only"):
        binary_metrics([0, 1], [.1, .9], .5, source=source)


@pytest.mark.parametrize("y,scores", [([0, 0], [.1, .2]), ([0, 1], [.1, np.nan]),
                                     ([0, 2], [.1, .2]), ([0, 1], [.1]), ([], [])])
def test_undefined_or_invalid_metrics_fail_closed(y, scores):
    with pytest.raises(ValueError):
        select_threshold(y, scores)


def test_score_ties_and_exact_threshold_search():
    y, scores = np.array([0, 1, 1, 0, 1, 0]), np.array([.1, .2, .2, .4, .5, .8])
    policy = select_threshold(y, scores)
    brute = [(binary_metrics(y, scores, t)["f2"], t) for t in np.unique(scores)]
    assert policy["threshold"] == max(brute)[1]
