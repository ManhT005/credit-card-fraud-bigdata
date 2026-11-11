# Phase 3 · pandas and Spark ETL benchmark

## Protocol

Use the original OpenML 1597 CSV and its successful Phase 1 acceptance record.
The benchmark verifies the input SHA-256 before preparing 1×, 10× and 100×
inputs. Replicas retain the input row ordinal as `source_row_id` and record
a zero-based `replica_id`. The pair is unique within each workload. These
inputs are reserved for ETL measurement and must stay outside ML experiments.

| Scale | Rows | Fraud labels |
|---|---:|---:|
| 1× | 284,807 | 492 |
| 10× | 2,848,070 | 4,920 |
| 100× | 28,480,700 | 49,200 |

Both engines read the same physical CSV files with explicit numeric types,
retain all fields and add `hour = floor(Time / 3600)`. Both write Snappy Parquet.
pandas streams batches of 50,000 rows through PyArrow. Spark processes its
input partitions through the DataFrame API. Each output is scanned after
timing to verify its schema, coverage of every source/copy ID, fraud count and
hour-by-class counts. The small integration fixture also compares every output
column by row identity.

The timer measures CSV read, transformation, and materialized Parquet write.
Input generation, Spark startup, Spark warm-up and Parquet validation are
outside the timer. Each timed run has a fresh process, and engine order
alternates. File-system caching is left to the host. Reports include per-run
elapsed time, sampled CPU seconds, sampled peak summed RSS, CSV and Parquet
bytes, input partitions, runtime versions, hardware, source hash and Git
revision. For pandas, input partitions are the number of CSV files processed.
Summary includes median, min, max and sample standard deviation across repeats.

The 100 ms sampler can miss short peaks and only measures the local process tree.
For Compose, Spark executor JVMs live in the worker containers, outside this
scope. Standalone CPU/RSS figures describe the driver and cannot be used for
a full-cluster resource comparison. The Docker topology shares one host and disk.

## Run locally

Install Java 17 and use a fresh environment. If the Phase 1 CSV and acceptance
artifact are already present and match, start at the benchmark command.

```bash
python -m pip install -r requirements/phase-02-linux-py311.txt
python -m pip install -r infra/docker/requirements.txt
python -m pip install --no-build-isolation --no-deps -e ".[data,notebook,dev,spark]"
python scripts/phase_01_acceptance.py
python scripts/phase_03_benchmark.py --scales 1 10 100 --repeats 3
```

Start with `--scales 1 --repeats 2` to verify setup. For 100× allow at least
30 GiB of free workspace and time for repeated writes. Set `--work-dir` to
a suitable local disk. Parquet is validated and cleaned up by default. Add
`--keep-parquet` to retain the final pair at each requested scale.

Open [the benchmark notebook](../notebooks/06_spark_etl_benchmark.ipynb)
after generating `artifacts/phase_03/benchmark.json`. It reads aggregate
measurements only. Use [Docker Compose](../infra/docker/README.md) for the
single-host standalone configuration. CI runs the original 1× workload in
both modes and uploads aggregate JSON only. Run all scales on the same
dedicated machine before comparing the full scale curve.
