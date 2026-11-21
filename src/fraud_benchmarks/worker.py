"""Run one timed ETL in a fresh process and sample its local resource usage."""

import argparse
import json
import os
import threading
import time
from pathlib import Path

import psutil

from fraud_benchmarks.etl import pandas_etl, spark_etl


class ResourceSample:
    def __init__(self):
        self.root = psutil.Process()
        self.cpu: dict[int, float] = {}
        self.peak_rss = 0

    def collect(self):
        rss = 0
        for process in [self.root, *self.root.children(recursive=True)]:
            try:
                with process.oneshot():
                    cpu = process.cpu_times()
                    rss += process.memory_info().rss
                self.cpu[process.pid] = cpu.user + cpu.system
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        self.peak_rss = max(self.peak_rss, rss)


def measure(operation) -> dict:
    sample = ResourceSample()
    sample.collect()
    baseline_cpu = sum(sample.cpu.values())
    stop = threading.Event()

    def monitor():
        while not stop.wait(0.1):
            sample.collect()

    thread = threading.Thread(target=monitor)
    thread.start()
    started = time.perf_counter()
    try:
        partitions = operation()
        elapsed = time.perf_counter() - started
    finally:
        stop.set()
        thread.join()
    sample.collect()
    return {
        "elapsed_seconds": elapsed,
        "cpu_seconds_sampled": sum(sample.cpu.values()) - baseline_cpu,
        "peak_rss_bytes_sampled": sample.peak_rss,
        "input_partitions": partitions,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=("pandas", "spark"))
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("metrics", type=Path)
    parser.add_argument("--master", required=True)
    parser.add_argument("--driver-memory", required=True)
    args = parser.parse_args()
    if args.engine == "pandas":
        import pandas  # noqa: F401 - import before starting the timer
        import pyarrow.parquet  # noqa: F401 - import before starting the timer

        metrics = measure(lambda: pandas_etl(args.source, args.output))
    else:
        from pyspark.sql import SparkSession

        os.environ["PYSPARK_SUBMIT_ARGS"] = f"--driver-memory {args.driver_memory} pyspark-shell"

        builder = (SparkSession.builder.master(args.master).appName("fraud-phase3-etl")
                   .config("spark.ui.enabled", "false")
                   .config("spark.cores.max", "2")
                   .config("spark.scheduler.minRegisteredResourcesRatio", "1.0")
                   .config("spark.scheduler.maxRegisteredResourcesWaitingTime", "60s")
                   .config("spark.executor.instances", "2")
                   .config("spark.executor.cores", "1")
                   .config("spark.executor.memory", "1g"))
        if os.environ.get("PHASE3_SPARK_DRIVER_HOST"):
            builder = builder.config("spark.driver.host", os.environ["PHASE3_SPARK_DRIVER_HOST"])
        spark = builder.getOrCreate()
        try:
            # Ensure the context and executors can run a job before measuring.
            spark.range(2, numPartitions=2).count()
            if args.master.startswith("spark://"):
                executors = spark.sparkContext._jsc.sc().getExecutorMemoryStatus().size() - 1
                if executors != 2:
                    raise RuntimeError(f"Expected two standalone executors, found {executors}")
            metrics = measure(lambda: spark_etl(spark, args.source, args.output))
            if args.master.startswith("spark://"):
                metrics["spark_registered_executors"] = executors
        finally:
            spark.stop()
    args.metrics.write_text(json.dumps(metrics, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
