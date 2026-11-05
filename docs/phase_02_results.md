# Phase 2 — Measured validation results (research review pending)

Base: origin/develop 24f6c4330d0890e9e133de6cbe004afd7326e0e5. Local execution used the working implementation with git_dirty=true; the implementation fingerprint below identifies the exact code/config. Hosted CI at the feature-branch head is a separate gate.

## Provenance

- CSV SHA-256: `f2de838bd0ef569a700976922711e2955fe057f806822a95a721ca55bdaa8080`.
- Primary split SHA-256: `25d7a9daf496855757b2c1b8e05bbe26f015c8aac43758cee25e4f56c168a690`.
- Config SHA-256: `91745395c04fd675051bc4cf80a57faae1fda3e22e974da609ae15b9abca7c3f`.
- Implementation SHA-256: `139ef522aecb7e8bc3240231afea056822d7795720b13978483c5b110b648d79`.
- Runtime versions: `{"imbalanced-learn": "0.14.2", "numpy": "2.3.5", "pandas": "2.2.3", "python": "3.12.14", "scikit-learn": "1.8.0", "xgboost": "3.4.1"}`.
- Hardware: `{"architecture": "x86_64", "logical_cpus": 9, "model_threads": 2, "omp_num_threads": "2", "openblas_num_threads": "2", "platform": "Linux-6.18.57-x86_64-with-glibc2.39"}`.

Actual source: 284807 rows, 492 fraud, 1081 exact duplicates retained. Cross-split exact-record overlap and feature-conflict groups are both zero.

| Primary partition | Rows | Fraud | Time minimum | Time maximum |
|---|---:|---:|---:|---:|
| test | 42721 | 52 | 151329 | 172792 |
| train | 199364 | 384 | 0 | 132928 |
| validation | 42722 | 56 | 132929 | 151328 |

These are integrity counts only. No held-out scores, thresholds or model metrics were computed. The source class rate drifts between periods, so chronological and random-reference scores must not be pooled.

## Primary chronological validation

| Candidate | AP | Precision | Recall | F2 | False alerts | Missed fraud | Fit/evaluate seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| dummy_prior | 0.001311 | 0.001311 | 1.000000 | 0.006520 | 42666 | 0 | 0.16 |
| logistic | 0.781488 | 0.700000 | 0.875000 | 0.833333 | 21 | 7 | 0.45 |
| logistic_balanced | 0.839355 | 0.846154 | 0.785714 | 0.797101 | 8 | 12 | 0.71 |
| logistic_smote | 0.811740 | 0.793103 | 0.821429 | 0.815603 | 12 | 10 | 0.95 |
| xgboost_01 | 0.846257 | 0.977778 | 0.785714 | 0.817844 | 1 | 12 | 1.75 |
| xgboost_02 | 0.831158 | 0.936170 | 0.785714 | 0.811808 | 3 | 12 | 2.56 |
| xgboost_03 | 0.832312 | 0.849057 | 0.803571 | 0.812274 | 8 | 11 | 3.59 |
| xgboost_04 | 0.819905 | 0.775862 | 0.803571 | 0.797872 | 13 | 11 | 2.28 |
| xgboost_05 | 0.821717 | 0.830189 | 0.785714 | 0.794224 | 9 | 12 | 3.46 |
| xgboost_06 | 0.833558 | 0.880000 | 0.785714 | 0.802920 | 6 | 12 | 4.54 |
| isolation_forest | 0.034727 | 0.051237 | 0.517857 | 0.183544 | 537 | 27 | 0.64 |

Thresholds are independently selected on the same validation partition by exact F2. AP is sklearn average precision, not trapezoidal PR area. Fit/evaluate time is measured locally for one run, not a repeat-run performance benchmark.

Proposed primary candidate: **xgboost_01**. Run ID: `chronological-xgboost_01-11e45772beb6`. Fitted model SHA-256: `afb1f6c336c9e46a654a3a3129c3cf9d416eced16780498d005950b6e5007f87`. Decision SHA-256: `528c36c09adbaef3a3c58319116376e30f0d84f9e75402d93d93316e89ced5fe`.

Validation operating threshold: `0.9685097932815552`; alerts/1000: `1.0533214737137775`. This is a research operating point on historical validation data, not a production cost or service-level commitment.

## Independent grouped-stratified reference

| Candidate | Reference validation AP | Reference validation F2 |
|---|---:|---:|
| dummy_prior | 0.001721 | 0.008548 |
| logistic | 0.768562 | 0.826693 |
| logistic_balanced | 0.737031 | 0.803571 |
| logistic_smote | 0.770874 | 0.816733 |
| xgboost_01 | 0.768950 | 0.841487 |
| xgboost_02 | 0.827155 | 0.843254 |
| xgboost_03 | 0.853181 | 0.851927 |
| xgboost_04 | 0.844048 | 0.835052 |
| xgboost_05 | 0.868899 | 0.857741 |
| xgboost_06 | 0.872854 | 0.865979 |
| isolation_forest | 0.141458 | 0.370370 |

The reference protocol keeps duplicate groups together; its row proportions are approximate. Its candidate never influences the primary proposal. These are validation comparisons, not held-out test results.

## Validation and closure status

- 45 non-kernel tests passed locally; Ruff and git diff whitespace checks passed.
- Four kernel test cases remain required in hosted CI. A local P1 kernel test fails because this environment prohibits socket binding (Operation not permitted), not because the data or notebook path contract passed kernel execution.
- Original-source modeling completed for 11 candidates in each of two protocols. No synthetic repetitions were used for empirical ML results.
- All four P2 notebooks are tested using original-data aggregate artifacts from root and notebooks/ via in-process IPython; saved local outputs identify that executor explicitly. Hosted CI executes real Jupyter kernels in both directories.
- CI retains the original P1 source job and adds P2 source, modeling and notebook gates; evidence uploads use an explicit aggregate-file allowlist.
- Two independent peer reviewers are still pending. accepted=false is intentional in P2 acceptance.json; technical execution cannot manufacture research approval.

## Limitations and next decision

Validation contains only 56 fraud events, so candidate selection and threshold estimates are uncertain and exposed to bounded-search selection bias. The two-day source window cannot establish longitudinal robustness; source PCA fit is unavailable. Fixed Time error slices are coarse (primary validation lies in the final 12-hour source slice); the slice table alone cannot establish temporal stability. The Public license field is not a specific SPDX grant. Precision@K ties follow stable validation row order, limiting interpretation for constant-risk Dummy. No accuracy-based winner, test performance, production readiness, or Spark speedup is claimed.

See phase_02_decision.md for the sign-off gate and P3/P4 backlog. The hosted artifact contains full per-run SHA/parameters, natural validation prevalence, train-only scaler/SMOTE evidence, aggregate PR/ROC curves, thresholds and error slices.
