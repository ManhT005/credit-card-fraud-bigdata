# Research notebooks

| Notebook | Scope |
|---|---|
| 01_data_profiling.ipynb | P1 source profiling and descriptive EDA |
| 02_split_and_leakage_audit.ipynb | P2 source/split SHA, coverage, Time groups, duplicate audit |
| 03_baseline_models.ipynb | P2 Dummy/logistic/balanced logistic, validation PR/ROC |
| 04_imbalance_experiments.ipynb | P2 SMOTE, six weighted XGB settings, IsolationForest; separate reference |
| 05_threshold_and_errors.ipynb | P2 validation F2 policy, alert volume, aggregate Amount/Time error slices |
| 06_spark_benchmark.ipynb | Planned P3; not implemented in Phase 2 |

Install `.[data,ml,notebook,dev]`. Run Phase 1 acceptance, then `python scripts/phase_02_acceptance.py --execute-notebooks`. P2 notebooks read source/config/code-verified aggregate experiment artifacts; reusable fitting, splitting and evaluation live in src/fraud_detection. Missing or stale evidence fails rather than silently using a different run. Notebook kernels can start in repo root or notebooks/; paths resolve through find_project_root.

Notebook outputs are not committed; CI saves executed copies in its aggregate artifact. No raw row previews, row-level predictions, invented metric values or test performance are included. Four P2 notebooks replace the old planned names to avoid duplicate functions; Spark stays Phase 3.
