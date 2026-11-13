"""Train-only candidates, validation-only selection, and aggregate evidence."""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import platform
import subprocess
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from fraud_detection.evaluation.metrics import aggregate_curves
from fraud_detection.evaluation.thresholds import select_threshold, threshold_summary
from fraud_detection.ingestion.profiling import FEATURE_COLUMNS
from fraud_detection.models.baselines import baseline_estimator, baseline_specs
from fraud_detection.models.candidates import candidate_estimator, risk_scores
from fraud_detection.preprocessing.manifest import (
    digest_json,
    split_manifest,
    verified_intake,
    write_json,
)
from fraud_detection.preprocessing.pipeline import build_pipeline, class_counts, select_features
from fraud_detection.preprocessing.split import chronological_split, stratified_reference_split


def load_config(root: Path) -> dict:
    config = yaml.safe_load((root / "configs/experiment.yaml").read_text())
    config["models"] = yaml.safe_load((root / "configs/phase_02_models.yaml").read_text())
    if (config["threshold_selection"] != {"dataset": "validation_only", "objective": "f2"}
            or config["evaluation"]["primary"] != "average_precision"
            or config["primary_split"]["strategy"] != "chronological"
            or config["resampling"]["smote"] != "train_only"):
        raise ValueError("Config violates the Phase 2 selection protocol")
    return config


def code_revision(root: Path) -> dict:
    def git(*args):
        try:
            return subprocess.check_output(["git", *args], cwd=root, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "unversioned_checkout"

    digest = hashlib.sha256()
    paths = sorted((root / "src/fraud_detection").rglob("*.py"))
    paths += sorted((root / "configs").glob("*.yaml"))
    for path in paths:
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return {"git_sha": git("rev-parse", "HEAD"), "git_dirty": bool(git("status", "--porcelain")),
            "implementation_sha256": digest.hexdigest()}


def prepare_splits(frame, intake, config, output: Path):
    primary = config["primary_split"]
    reference = config["reference_split"]
    if not np.isclose(sum(primary[k] for k in (
            "train_fraction", "validation_fraction", "test_fraction")), 1):
        raise ValueError("Primary split fractions must sum to one")
    if not np.isclose(sum(reference[k] for k in (
            "train_fraction", "validation_fraction", "test_fraction")), 1):
        raise ValueError("Reference split fractions must sum to one")
    split = chronological_split(frame, primary["train_fraction"], primary["validation_fraction"])
    ref = stratified_reference_split(frame, config["seed"], reference["train_fraction"],
                                     reference["validation_fraction"])
    manifest = split_manifest(frame, split, intake, config)
    reference_manifest = split_manifest(frame, ref, intake, config)
    write_json(output / "dataset_intake.json", intake)
    write_json(output / "split_manifest.json", manifest)
    write_json(output / "reference_split_manifest.json", reference_manifest)
    return split, manifest, ref, reference_manifest


def slice_errors(frame, scores, threshold: float) -> dict:
    """Fixed, documented slices of validation; no row-level examples are published."""
    predicted = scores >= threshold
    actual = frame.Class.to_numpy().astype(bool)
    result = {}
    for name, edges in (("Amount", [-np.inf, 10, 100, 1000, np.inf]),
                        ("Time", [-np.inf, 43200, 86400, 129600, np.inf])):
        bins = pd.cut(frame[name], bins=edges, right=False)
        rows = []
        for label in bins.cat.categories:
            mask = (bins == label).to_numpy()
            rows.append({"slice": str(label), "rows": int(mask.sum()),
                         "fraud": int((actual & mask).sum()),
                         "alerts": int((predicted & mask).sum()),
                         "fp": int((predicted & ~actual & mask).sum()),
                         "fn": int((~predicted & actual & mask).sum())})
        result[name] = rows
    return result


def package_versions() -> dict:
    result = {"python": platform.python_version()}
    for name in ("numpy", "pandas", "scikit-learn", "imbalanced-learn", "xgboost"):
        try:
            result[name] = version(name)
        except PackageNotFoundError:
            result[name] = "not installed"
    return result


def model_specs(config: dict) -> list[dict]:
    specs = baseline_specs()
    grid = config["models"]["xgboost_grid"]
    if not 6 <= len(grid) <= 12:
        raise ValueError("The frozen XGBoost grid must contain 6–12 candidates")
    for i, parameters in enumerate(grid):
        if set(parameters) != {"n_estimators", "max_depth"}:
            raise ValueError("Only the reviewed bounded XGBoost parameters may vary")
        if not (1 <= parameters["n_estimators"] <= 500 and 1 <= parameters["max_depth"] <= 8):
            raise ValueError("XGBoost grid exceeds the bounded CPU budget")
        specs.append({"name": f"xgboost_{i+1:02d}", "kind": "xgboost",
                      "balance": "scale_pos_weight", "parameters": parameters})
    if config["models"]["isolation_forest"]:
        specs.append({"name": "isolation_forest", "kind": "isolation_forest", "balance": "none"})
    return specs


def run_experiment(frame: pd.DataFrame, split, manifest: dict, config: dict,
                   output: Path, revision: dict, *, specs: list[dict] | None = None) -> dict:
    """Only train and validation partitions enter this code. Test indices are never scored."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    train, val = frame.iloc[split.train], frame.iloc[split.validation]
    X_train, X_val = select_features(train), select_features(val)
    y_train, y_val = train.Class.to_numpy().astype(int), val.Class.to_numpy().astype(int)
    versions = package_versions()
    runs, comparisons = [], []
    config_sha = digest_json(config)
    for spec in model_specs(config) if specs is None else specs:
        start = time.perf_counter()
        if spec["kind"] in ("dummy", "logistic"):
            estimator = baseline_estimator(spec, config["seed"])
        else:
            estimator = candidate_estimator(spec, y_train, config["seed"], config["models"]["threads"])
        sampling = config["models"]["smote"]
        pipeline = build_pipeline(estimator, smote=spec["balance"] == "smote",
            seed=config["seed"], k_neighbors=sampling["k_neighbors"],
            sampling_strategy=sampling["sampling_strategy"])
        # Passing y to IsolationForest would be ignored; omit it for the unsupervised comparison.
        pipeline.fit(X_train, None if spec["kind"] == "isolation_forest" else y_train)
        scores = risk_scores(pipeline, X_val, kind=spec["kind"])
        policy = select_threshold(y_val, scores, source="validation")
        runtime = time.perf_counter() - start
        scaler = pipeline.named_steps["features"].named_transformers_["features"].named_steps["scaler"]
        model_digest = hashlib.sha256(pickle.dumps(estimator, protocol=4))
        model_digest.update(scaler.mean_.tobytes())
        model_digest.update(scaler.scale_.tobytes())
        identity = {"source": manifest["dataset"]["original_csv_sha256"],
                    "split": manifest["split_sha256"], "config": config_sha,
                    "code": revision["implementation_sha256"], "spec": spec,
                    "versions": versions}
        run_id = f"{split.strategy}-{spec['name']}-{digest_json(identity)[:12]}"
        before = class_counts(y_train)
        after = (pipeline.named_steps["smote"].output_class_counts_
                 if spec["balance"] == "smote" else before)
        effective_parameters = {
            key: "NaN (library missing sentinel)" if isinstance(value, float) and np.isnan(value)
            else value for key, value in estimator.get_params().items()
        }
        run = {"run_id": run_id, "original_csv_sha256": identity["source"],
               "split_sha256": identity["split"], "config_sha256": config_sha,
               **revision, "versions": versions, "seed": config["seed"],
               "feature_order": list(FEATURE_COLUMNS), "model_name": spec["name"],
               "kind": spec["kind"], "balance_strategy": spec["balance"],
               "hyperparameters": effective_parameters,
               "fit_source": "train", "evaluation_source": "validation", "test_opened": False,
               "train_rows": len(train), "validation_rows": len(val),
               "train_class_counts_before": before, "train_class_counts_after": after,
               "validation_class_counts": class_counts(y_val),
               "scaler_fit_rows": int(scaler.n_samples_seen_),
               "hardware": {"platform": platform.platform(), "architecture": platform.machine(),
                            "logical_cpus": os.cpu_count(), "model_threads": config["models"]["threads"],
                            "omp_num_threads": os.environ.get("OMP_NUM_THREADS", "not set"),
                            "openblas_num_threads": os.environ.get("OPENBLAS_NUM_THREADS", "not set")},
               "runtime_seconds": runtime, "fitted_model_sha256": model_digest.hexdigest(),
               "validation_metrics": policy["metrics"], "threshold_policy": policy,
               "curves": aggregate_curves(y_val, scores),
               "threshold_summary": threshold_summary(y_val, scores),
               "error_slices": slice_errors(val, scores, policy["threshold"])}
        run_dir = output / "runs" / run_id
        write_json(run_dir / "run_manifest.json", run)
        write_json(run_dir / "validation_metrics.json", policy["metrics"])
        write_json(run_dir / "threshold_policy.json", policy)
        runs.append(run)
        metrics = policy["metrics"]
        comparisons.append({"run_id": run_id, "split_strategy": split.strategy,
            "split_sha": identity["split"], "model": spec["name"],
            "balance_strategy": spec["balance"], "ap_val": metrics["average_precision"],
            "roc_auc_val": metrics["roc_auc"], "precision_val": metrics["precision"],
            "recall_val": metrics["recall"], "f1_val": metrics["f1"], "f2_val": metrics["f2"],
            "threshold_val": policy["threshold"], "alerts_val": metrics["alerts"],
            "fp_val": metrics["fp"], "fn_val": metrics["fn"], "runtime_seconds": runtime,
            "seed": config["seed"], "git_sha": revision["git_sha"]})
        print(f"{run_id}: AP_val={metrics['average_precision']:.6f} F2_val={metrics['f2']:.6f}",
              flush=True)
    if not runs:
        raise ValueError("At least one candidate is required")
    champion = min(runs, key=lambda r: (-r["validation_metrics"]["average_precision"],
        -r["validation_metrics"]["f2"], r["model_name"]))
    candidate = {"run_id": champion["run_id"], "model_name": champion["model_name"],
                 "fitted_model_sha256": champion["fitted_model_sha256"],
                 "threshold_policy": champion["threshold_policy"],
                 "selection": "maximum validation AP; then F2; then model name",
                 "status": "proposed_pending_two_reviewers", "reviewers": [],
                 "test_opened": False, "split_sha256": manifest["split_sha256"]}
    candidate["decision_sha256"] = digest_json(candidate)
    result = {"runs": runs, "candidate": candidate, "comparison": comparisons,
              "test_opened": False, "split_sha256": manifest["split_sha256"],
              "config_sha256": config_sha, "source_kind": manifest["dataset"]["source_kind"]}
    pd.DataFrame(comparisons).to_csv(output / "model_comparison.csv", index=False)
    write_json(output / "candidate_proposal.json", candidate)
    write_json(output / "experiment.json", result)
    return result


def run_from_root(root: Path, *, include_reference: bool = True) -> dict:
    config, output = load_config(root), root / "artifacts/phase_02"
    frame, intake = verified_intake(root / "data/raw/creditcard.csv", root / "artifacts/phase_01")
    split, manifest, ref, ref_manifest = prepare_splits(frame, intake, config, output)
    revision = code_revision(root)
    result = run_experiment(frame, split, manifest, config, output, revision)
    if include_reference:
        # Independent reference; it cannot replace or influence the primary proposal.
        reference = run_experiment(frame, ref, ref_manifest, config, output / "reference", revision)
        result["reference_candidate"] = reference["candidate"]
    write_json(output / "experiment.json", result)
    return result


def load_verified_results(root: Path) -> dict:
    """Read aggregate notebook inputs only when source, config and code still match."""
    output = root / "artifacts/phase_02"
    result = json.loads((output / "experiment.json").read_text())
    intake = json.loads((output / "dataset_intake.json").read_text())
    from fraud_detection.ingestion.profiling import sha256_file

    if (intake["original_csv_sha256"] != sha256_file(root / "data/raw/creditcard.csv")
            or result["config_sha256"] != digest_json(load_config(root))
            or any(run["implementation_sha256"] != code_revision(root)["implementation_sha256"]
                   for run in result["runs"])):
        raise ValueError("Stale experiment artifacts; rerun Phase 2 acceptance")
    return result
