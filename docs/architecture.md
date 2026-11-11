# System architecture

```text
OpenML 1597
    |
    v
Ingestion -> Schema checks -> Raw local data
    |
    v
Split -> Preprocessing -> Feature engineering
    |                             |
    |                             +--> scikit-learn / XGBoost
    |                                       |
    |                                       v
    |                              Evaluation -> Reports -> Dashboard
    |
    +--> Spark ETL -> Parquet -> pandas/Spark benchmark
```

## Module responsibilities

- `ingestion`: source retrieval, provenance and schema checks.
- `preprocessing`: split management and leakage-safe transformations.
- `features`: deterministic feature engineering.
- `models`: classification and anomaly-detection baselines.
- `evaluation`: PR analysis, fraud-alert thresholds and error diagnostics.
- `fraud_benchmarks`: ETL scaling, elapsed time and memory comparisons. Its separate
  package keeps benchmark changes outside the Phase 2 implementation fingerprint.
- `pipelines`: commands shared by scripts and notebooks.

## Spark deployment stages

1. Local PySpark for reproducible ETL.
2. Docker Compose with one master and two workers for an educational cluster.
3. Optional multi-host test if resources permit.

The original ~285k-row dataset does not itself require a distributed cluster.
Measure performance rather than presuming Spark is faster. Multiple Docker
workers on one laptop are not a true multi-node hardware benchmark.

See [the standalone Compose setup](../infra/docker/README.md) for local deployment.
