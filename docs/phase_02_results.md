# Phase 2 — Hosted CI validation results

Source of record: [GitHub Actions run 42364868665](https://github.com/ManhT005/credit-card-fraud-bigdata/actions/runs/42364868665), artifact `13570879627` (SHA-256 `77fde42ecdc3ff1cf11790e535840aea7126f051f9d5c221959c451527b6edc9`). PR head `62f5108b511857fd96ac30ab53cb96a7c8090333`; executed checkout `d615be88b585fc2bbf6a64881dee643f32a77386`.

## Provenance

- CSV SHA-256: `f2de838bd0ef569a700976922711e2955fe057f806822a95a721ca55bdaa8080`.
- Primary split SHA-256: `25d7a9daf496855757b2c1b8e05bbe26f015c8aac43758cee25e4f56c168a690`.
- Config SHA-256: `91745395c04fd675051bc4cf80a57faae1fda3e22e974da609ae15b9abca7c3f`.
- Implementation SHA-256: `139ef522aecb7e8bc3240231afea056822d7795720b13978483c5b110b648d79`.
- Runtime versions: `{"imbalanced-learn":"0.14.2","numpy":"2.4.6","pandas":"3.1.1","python":"3.11.18","scikit-learn":"1.9.1","xgboost":"3.2.0"}`.
- Hardware: `{"architecture":"x86_64","logical_cpus":4,"model_threads":2,"omp_num_threads":"2","openblas_num_threads":"2","platform":"Linux-7.0.0-1019-azure-x86_64-with-glibc2.43"}`.

OpenML 1597 contains 284807 rows and 492 fraud cases. All 1081 exact duplicate rows were retained. Cross-split record overlap was 0 and conflicting feature groups numbered 0.

| Primary partition | Rows | Fraud | Time minimum | Time maximum |
|---|---:|---:|---:|---:|
| train | 199364 | 384 | 0 | 132928 |
| validation | 42722 | 56 | 132929 | 151328 |
| test | 42721 | 52 | 151329 | 172792 |

The held-out test stays sealed. Test partition counts describe split integrity only. Compare each protocol separately because the chronological class rate drifts.

## Primary chronological validation

| Candidate | AP | Precision | Recall | F2 | False alerts | Missed fraud | Fit/evaluate seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| dummy_prior | 0.001311 | 0.001311 | 1.000000 | 0.006520 | 42666 | 0 | 0.13 |
| logistic | 0.781488 | 0.700000 | 0.875000 | 0.833333 | 21 | 7 | 0.27 |
| logistic_balanced | 0.839355 | 0.846154 | 0.785714 | 0.797101 | 8 | 12 | 0.46 |
| logistic_smote | 0.811740 | 0.793103 | 0.821429 | 0.815603 | 12 | 10 | 0.50 |
| xgboost_01 | 0.838221 | 0.936170 | 0.785714 | 0.811808 | 3 | 12 | 1.04 |
| xgboost_02 | 0.829546 | 0.916667 | 0.785714 | 0.808824 | 4 | 12 | 1.47 |
| xgboost_03 | 0.837251 | 0.833333 | 0.803571 | 0.809353 | 9 | 11 | 1.95 |
| xgboost_04 | 0.813831 | 0.877551 | 0.767857 | 0.787546 | 6 | 13 | 1.23 |
| xgboost_05 | 0.822579 | 0.725806 | 0.803571 | 0.786713 | 17 | 11 | 1.93 |
| xgboost_06 | 0.839861 | 0.766667 | 0.821429 | 0.809859 | 14 | 10 | 2.64 |
| isolation_forest | 0.034727 | 0.051237 | 0.517857 | 0.183544 | 537 | 27 | 0.38 |

Each threshold maximizes F2 on validation. AP is scikit-learn average precision. Timings describe this CI execution.

Proposed candidate: **xgboost_06**. Run ID: `chronological-xgboost_06-1f4d95e0f797`. Fitted model SHA-256: `94dfe90f1c08d1e0933d6c5366c897c8b3a5e0d5c2e6778272ef2982df83c31f`. Decision SHA-256: `1602082a03abe686b8c828bc3bbac9711163461fcec65e459f51e6da4dafe00a`.

Validation threshold: `0.08604497462511063`. Alerts per 1,000 transactions: 1.404429.

## Independent grouped-stratified reference

| Candidate | Reference validation AP | Reference validation F2 |
|---|---:|---:|
| dummy_prior | 0.001686 | 0.008373 |
| logistic | 0.748850 | 0.790554 |
| logistic_balanced | 0.713944 | 0.809129 |
| logistic_smote | 0.753318 | 0.824742 |
| xgboost_01 | 0.724359 | 0.821206 |
| xgboost_02 | 0.816430 | 0.829918 |
| xgboost_03 | 0.841930 | 0.833333 |
| xgboost_04 | 0.820442 | 0.822785 |
| xgboost_05 | 0.837159 | 0.835118 |
| xgboost_06 | 0.843842 | 0.844017 |
| isolation_forest | 0.095209 | 0.269865 |

The reference split keeps duplicate groups together. The primary decision uses only chronological validation.

## Reproducibility and acceptance

- Previous local execution (CPython 3.12.14, XGBoost 3.4.1) proposed `xgboost_01` at AP 0.846257. The original hosted run (CPython 3.11.18, XGBoost 3.2.0) proposed `xgboost_06` at AP 0.839861. The two executions had the same source, split, configuration and implementation fingerprints. NumPy, pandas, scikit-learn and platform versions also differed, so the comparison identifies runtime drift without isolating one dependency.
- The locked workflow trained both protocols twice in separate processes. The primary proposal files matched byte for byte, and the decision hash reproduced the original hosted result.
- The verified CI artifact records 11 candidates per protocol, 8 notebook executions and sealed test data. Independent source/split and model/evaluation sign-offs are tracked in [the decision record](phase_02_decision.md).

## Limitations and next decision

Validation contains only 56 fraud events, so candidate selection and threshold estimates are uncertain and exposed to bounded-search selection bias. The two-day source window cannot establish longitudinal robustness; source PCA fit is unavailable. Fixed Time error slices are coarse (primary validation lies in the final 12-hour source slice); the slice table alone cannot establish temporal stability. The Public license field is not a specific SPDX grant. Precision@K ties follow stable validation row order, limiting interpretation for constant-risk Dummy. No accuracy-based winner, test performance, production readiness, or Spark speedup is claimed.

See [the decision record](phase_02_decision.md) for the research gate. The hosted artifact contains per-run parameters, train-only preprocessing and SMOTE evidence, aggregate curves, operating thresholds and error slices.
