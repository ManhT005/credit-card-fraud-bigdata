# Phase 1 — Data acquisition and profiling

**Branch:** feature/phase-01-data-profiling, based on develop.
**Status:** implementation with automated original-source acceptance; use the CI result and evidence for the reviewed revision.

## Responsibilities (5-person team)

| Task | Owner | Deliverable |
|---|---|---|
| P1-01 Integration | N1 / Tech Lead | Profiling CLI, Spark smoke check, CI review |
| P1-02 Source integrity | N2 / Data Engineer | Verify download, license, version, SHA-256, schema, nulls and duplicates |
| P1-03 Imbalance | N3 / ML | Fraud rate, majority-only accuracy paradox, split and leakage risk |
| P1-04 Statistical exploration | N4 / DS | Amount/Time statistics, PCA feature cautions, outlier investigation |
| P1-05 Quality and reporting | N5 / QA | Run notebook, review source, document reproducibility and findings |

## How to run

1. Download OpenML 1597 original `creditcard.csv`, place at `data/raw/creditcard.csv`. Never commit source transactions.
2. `python -m pip install -e ".[data,notebook,dev]"`
3. `fraud-bigdata profile --input data/raw/creditcard.csv --output artifacts/phase_01`
4. Run `notebooks/01_data_profiling.ipynb` from repository root or `notebooks/`. Or run `python scripts/phase_01_acceptance.py` to download the pinned source and execute all notebook cells automatically.
5. `python -m pytest -q`; `python -m ruff check src tests scripts dashboard`.
6. Optional: install `.[spark]`, run `python scripts/spark_inspection.py` (not a benchmark).

## Definition of Done

- [ ] Dataset version and reuse license reviewed with source link and local SHA-256.
- [ ] 31 fields and binary Class validated on actual CSV.
- [ ] Actual row and fraud counts recorded and reference mismatch checked.
- [ ] Null/non-numeric/non-finite/invalid/duplicate findings reviewed.
- [ ] Mean/median/P99, class balance and PCA plots executed.
- [ ] Risks: duplicate overlap, train-only fitting, resampling leakage, time window.
- [ ] Test, lint, notebook and PR review evidence recorded.

Do not claim data-quality findings, Spark benchmark gains or fraud-model metrics until actual experiments run. No SMOTE, scaler fitting, feature engineering or model training in Phase 1.

## Course mapping

- Preprocessing lecture: CSV/Parquet, missingness, scaling, PCA, leakage.
- `bigdata_analytics_p1.ipynb`: mean, median, P99, skew/distribution.
- `BDA_PySpark.ipynb`: Spark CSV read, schema, aggregation.
- Assignment: acquisition → EDA → cleaning → features → modeling → evaluation → demo.
