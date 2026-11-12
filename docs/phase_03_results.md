# Phase 3 measured ETL results

Measured code revision `3bec3b0c689973b3b2b8b54bce0a5f08d64322be`, clean checkout.
Source CSV SHA-256 `f2de838bd0ef569a700976922711e2955fe057f806822a95a721ca55bdaa8080`.
Each engine ran twice per scale with alternating order.

| Scale | Rows | pandas median seconds | Spark median seconds |
|---|---:|---:|---:|
| 1× | 284,807 | 2.526 | 2.987 |
| 10× | 2,848,070 | 22.813 | 15.096 |
| 100× | 28,480,700 | 235.817 | 129.417 |

These results describe the local `local[2]` workload.
Runtime versions were `{"pandas": "2.2.3", "psutil": "7.2.2", "pyarrow": "26.0.1", "pyspark": "3.5.8"}`, Python 3.12.14 and `openjdk version "21.0.13" 2026-10-20`.
See [local aggregate evidence](../reports/phase_03/local_benchmark.json) for every timing, sampled resource measurement, output byte count, partition count, environment and parity audit.

## Hosted verification

[Actions run 42947881498](https://github.com/ManhT005/credit-card-fraud-bigdata/actions/runs/42947881498) passed all four jobs on the measured code revision. Its original-data 1× checks exercised local Spark and the Compose topology with two registered executors. The verified artifact was `13824471016`, ZIP SHA-256 `80a647efed0065983f1dad286c863b1077c6efc07e5a693df7cf24570fdbdca8`.

The stored [CI local report](../reports/phase_03/ci_local_benchmark.json) and [CI standalone report](../reports/phase_03/ci_standalone_benchmark.json) record that runner's locked dependencies and Java 17. Local measurements used Java 21 and the versions above. Compare scale trends within the same environment. Timings vary with CPU, disk, runtime and caches.

Parquet schema, full identity coverage, fraud totals and hour/class aggregates passed at all scales. The integration fixture passed full-column equality. The local Phase 3 notebook cells executed against aggregate results. Four earlier notebook tests encountered a local Jupyter kernel startup restriction. The hosted workflow passed the complete kernel test and acceptance gates.

Two repetitions give an initial variation estimate. The default protocol uses three repetitions. Spark startup and input preparation are outside the measured interval, and standalone resource sampling covers the driver process tree. See [the protocol](phase_03_benchmark.md).
