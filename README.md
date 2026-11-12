# Credit Card Fraud Detection — Big Data Analytics

Reproducible research scaffold for **Apache Spark, imbalanced machine learning, and fraud risk analytics**.

**Current status:** Phase 1 verified-source tooling plus Phase 2 leakage-safe modeling/evaluation. Validation results and proposal require hosted CI and independent peer review; held-out test remains sealed. Phase 3 adds reproducible pandas and Spark ETL benchmarks.

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
│   ├── pipelines/              # End-to-end orchestration
│   └── cli.py
├── src/fraud_benchmarks/        # pandas versus Spark
├── dashboard/                  # Streamlit research dashboard
├── infra/docker/               # Spark standalone cluster
├── scripts/                    # Repeatable acceptance entrypoints
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

python -m pip install -e ".[data,ml,notebook,dev]"
fraud-bigdata info
python -m pytest -q
```

Optional packages for Spark and the dashboard:

```bash
python -m pip install -e ".[data,ml,spark,dev]"
python -m pip install -e ".[dashboard]"
streamlit run dashboard/app.py
```

The dashboard presents verified research results from checked-in aggregates.
Docker Compose runs the Phase 3 Spark standalone topology. Phase 1 local CSV profiling is implemented.

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
| 1 | Local OpenML CSV profiling and exploratory notebook | Implemented; verified-source acceptance job retained |
| 2 | ML baselines and evaluation | Implemented; research sign-off pending |
| 3 | Spark ETL and performance study | Implemented; see benchmark protocol and CI evidence |
| 4 | Streamlit demo and final report | Implemented; held-out test sealed |

## Phase 1: Data profiling and notebook

Download the original dataset from [OpenML 1597](https://www.openml.org/d/1597) and place `creditcard.csv` in `data/raw/` locally (ignored by Git).

```bash
python -m pip install -e ".[data,notebook,dev]"
fraud-bigdata profile --input data/raw/creditcard.csv --output artifacts/phase_01
python -m pytest -q
python -m ruff check src tests scripts dashboard
jupyter notebook notebooks/01_data_profiling.ipynb
```

Optional Spark smoke check: install `.[spark]`, then run `python scripts/spark_inspection.py`. It is not a performance benchmark.

Read the [Phase 1 team task plan](docs/phase_01_tasks.md) and [data card](docs/phase_01_data_card.md). Run `python scripts/phase_01_acceptance.py` to download and verify the pinned original ARFF, export all 31 columns to local CSV, and execute the notebook from `notebooks/`. The `phase-1-acceptance` CI job publishes aggregate evidence; acceptance requires this job and tests to pass on the PR revision. See the data card for the source-declared `Public` license limitation.

## License

See [LICENSE](LICENSE).

## Phase 2: Leakage-safe modeling and evaluation

Use Ubuntu 26.04 x86_64 and CPython 3.11.18 in a fresh virtual environment for parity with CI. The generic setup above is for development. For comparable Phase 2 results, use the locked environment below.

```bash
python -m pip install -r requirements/phase-02-linux-py311.txt
python -m pip install --no-build-isolation --no-deps -e ".[data,ml,notebook,dev]"
python -m pip check
export MPLBACKEND=Agg OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
python scripts/phase_01_acceptance.py
python scripts/phase_02_acceptance.py --execute-notebooks
python -m pytest -q
python -m ruff check src tests scripts dashboard
```

The verified original CSV is required. Primary Time-group split (70/15/15) and independent grouped-stratified reference (approximately 60/20/20) retain all rows and block cross-split duplicates. The pipeline trains Dummy prior, logistic, balanced logistic, train-only SMOTE logistic, six weighted XGBoost candidates and Isolation Forest per protocol. Selection uses validation AP; each threshold uses validation F2. Test remains sealed.

Read the [protocol](docs/phase_02_protocol.md), [measured validation results](docs/phase_02_results.md), and [review gate](docs/phase_02_decision.md). Technical CI success does not approve a research champion. Artifacts contain aggregate evidence and no raw transactions, per-row predictions or model binaries.

Kernel execution requires local socket support. In restricted environments, `pytest -m "not notebook"` runs the non-kernel contracts only; it is not full acceptance. Hosted CI runs all tests and original-data notebooks.

## Phase 3: Spark ETL and performance study

Run the [benchmark protocol](docs/phase_03_benchmark.md) to compare pandas and Spark on verified 1×, 10× and 100× ETL workloads. The [Docker topology](infra/docker/README.md) supports a standalone master and two workers.

## Phase 4: Dashboard and final report

Run `python -m pip install -e ".[dashboard]"` and `python -m streamlit run dashboard/app.py` from the repository root. The demo uses checked-in aggregate evidence. See the [final report and demo walkthrough](docs/phase_04_final_report.md).
