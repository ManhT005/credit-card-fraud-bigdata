# Credit Card Fraud Detection — Big Data Analytics

Reproducible research scaffold for **Apache Spark, imbalanced machine learning, and fraud risk analytics**.

**Current status:** Project skeleton plus Phase 1 read-only profiling, EDA notebook and synthetic tests. No trained models or measured benchmark results.

## Objectives

1. Study credit card fraud classification under extreme class imbalance.
2. Compare logistic regression, class weights, SMOTE, XGBoost and Isolation Forest.
3. Optimize decision thresholds using validation data and PR-AUC/AP metrics.
4. Benchmark pandas versus PySpark ETL at 1x, 10x, and 100x dataset scales.

## Dataset

[OpenML Credit Card Fraud — ID 1597](https://www.openml.org/d/1597):
284,807 transactions; 492 fraud labels; target `Class`;
features `V1`–`V28`, `Amount`, and `Time`.

Do not commit raw transactions or replicated benchmark data.

## Project structure

```text
.
├── .github/workflows/          # Python CI
├── configs/                    # Data and experiment config
├── data/
│   ├── raw/                    # Original dataset
│   ├── processed/              # Intermediate and Parquet data
│   └── benchmark/              # Scale-test inputs only
├── docs/                       # Research and architecture notes
├── notebooks/                  # EDA and analysis
├── src/fraud_detection/
│   ├── ingestion/              # OpenML retrieval and validation
│   ├── preprocessing/          # Splits, leakage prevention
│   ├── features/               # Feature engineering
│   ├── models/                 # Training methods
│   ├── evaluation/             # Metrics and thresholds
│   ├── benchmarks/             # pandas versus Spark
│   ├── pipelines/              # End-to-end orchestration
│   └── cli.py
├── dashboard/                  # Streamlit placeholder
├── infra/docker/               # Planned Spark cluster
├── scripts/                    # Repeatable entrypoints (planned)
├── artifacts/                  # Local results, ignored
├── reports/                    # Research deliverables
└── tests/
```

## Quick start

Python 3.10+ is required. PySpark also requires a Java runtime compatible
with the chosen Spark version.

```bash
git clone https://github.com/ManhT005/credit-card-fraud-bigdata.git
cd credit-card-fraud-bigdata
git switch develop

python -m venv .venv
# Windows Git Bash: source .venv/Scripts/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate

python -m pip install -e ".[dev]"
fraud-bigdata info
python -m pytest -q
```

Optional packages for future phases:

```bash
python -m pip install -e ".[data,ml,spark,dev]"
python -m pip install -e ".[dashboard]"
streamlit run dashboard/app.py
```

The dashboard is deliberately a placeholder, not a trained fraud classifier.
Docker Compose and production ingestion are planned for later phases. Phase 1 local CSV profiling is implemented.

## Research safeguards

- Split train, validation and test **before** fitting transformations or applying SMOTE.
- Preserve natural fraud prevalence in validation/test.
- Use the chronological split for the primary experiment, plus a stratified reference.
- Select thresholds only on validation; report held-out test performance once.
- Primary metric: **average precision (AP)**; also evaluate recall, precision,
  F1/F2, ROC-AUC, confusion matrix and alert volume.
- Replicated 10x/100x data is **ETL benchmark-only**, not independent ML data.

Read [experiment protocol](docs/experiment_protocol.md) and
[architecture](docs/architecture.md) before implementing models.

## Milestones

| Phase | Goal | Status |
| --- | --- | --- |
| 0 | Skeleton, package, smoke tests | Scaffold |
| 1 | Local OpenML CSV profiling and exploratory notebook | Implemented (original-data validation pending) |
| 2 | ML baselines and evaluation | Planned |
| 3 | Spark ETL and performance study | Planned |
| 4 | Streamlit demo and final report | Planned |

## Phase 1: Data profiling and notebook

Download the original dataset from [OpenML 1597](https://www.openml.org/d/1597) and place `creditcard.csv` in `data/raw/` locally (ignored by Git).

```bash
python -m pip install -e ".[data,ml,dev]"
fraud-bigdata profile --input data/raw/creditcard.csv --output artifacts/phase_01
python -m pytest -q
python -m ruff check src tests scripts dashboard
jupyter notebook notebooks/01_data_profiling.ipynb
```

Optional Spark smoke check: install `.[spark]`, then run `python scripts/spark_inspection.py`. It is not a performance benchmark.

Read the [Phase 1 team task plan](docs/phase_01_tasks.md) and [data card](docs/phase_01_data_card.md). The local dataset must be executed before any actual findings or Phase 1 acceptance are claimed.

## License

See [LICENSE](LICENSE).
