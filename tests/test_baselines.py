import json

import numpy as np

from fraud_detection.models.baselines import baseline_specs
from fraud_detection.pipelines.train import load_config, prepare_splits, run_experiment
from fraud_detection.preprocessing.manifest import digest_json


def experiment_fixture(frame, output):
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    config = load_config(root)
    intake = {"source_kind": "synthetic_fixture", "original_csv_sha256": digest_json("fixture")}
    split, manifest, _, _ = prepare_splits(frame, intake, config, output)
    revision = {"git_sha": "synthetic", "git_dirty": True, "implementation_sha256": "fixture"}
    return config, split, manifest, revision


def test_baselines_replay_and_test_features_never_enter_training(fraud_frame, tmp_path):
    config, split, manifest, revision = experiment_fixture(fraud_frame, tmp_path)
    specs = baseline_specs()[:3]
    first = run_experiment(fraud_frame, split, manifest, config, tmp_path, revision, specs=specs)
    poisoned = fraud_frame.copy()
    poisoned.iloc[split.test, poisoned.columns.get_loc("Amount")] = np.nan
    poisoned.iloc[split.test, poisoned.columns.get_loc("Class")] = 2
    second = run_experiment(poisoned, split, manifest, config, tmp_path / "replay", revision,
                            specs=specs)
    assert first["candidate"]["run_id"] == second["candidate"]["run_id"]
    for a, b in zip(first["runs"], second["runs"]):
        assert a["validation_metrics"] == b["validation_metrics"]
        assert a["fitted_model_sha256"] == b["fitted_model_sha256"]
        assert a["scaler_fit_rows"] == len(split.train)
        assert not a["test_opened"] and a["fit_source"] == "train"
    assert first["candidate"]["reviewers"] == []
    assert first["candidate"]["status"] == "proposed_pending_two_reviewers"
    saved = json.loads((tmp_path / "experiment.json").read_text())
    assert saved["source_kind"] == "synthetic_fixture"
    assert "predictions" not in saved and "test_metrics" not in saved
