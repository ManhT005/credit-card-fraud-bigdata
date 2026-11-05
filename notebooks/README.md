# Notebooks

1. `01_data_profiling.ipynb` — **implemented Phase 1**: schema, provenance, missingness, class imbalance, descriptive statistics, PCA display, leakage risks.
2. `02_model_baselines.ipynb` — planned.
3. `03_threshold_analysis.ipynb` — planned.
4. `04_spark_benchmark.ipynb` — planned.

Phase 1: install `.[data,notebook,dev]`, place CSV at `data/raw/creditcard.csv`, launch Jupyter from repository root or `notebooks/`. Notebook uses reusable functions in `src/fraud_detection/ingestion/profiling.py` and has no saved outputs. It does not train or resample. See `docs/phase_01_tasks.md`.

The notebook resolves repository paths automatically from both the repository root and `notebooks/`. For original-data verification and a saved executed notebook, run `python scripts/phase_01_acceptance.py`.
