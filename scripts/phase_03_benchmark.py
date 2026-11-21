"""Run Phase 3 ETL benchmarks using a verified Phase 1 CSV and acceptance record."""

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory

import psutil
import yaml

from fraud_benchmarks.etl import PANDAS_BATCH_ROWS, audit_output, prepare_input
from fraud_detection.ingestion.profiling import (
    EXPECTED_ORIGINAL_FRAUD,
    EXPECTED_ORIGINAL_ROWS,
    sha256_file,
)

ROOT = Path(__file__).resolve().parents[1]
ENGINES = ("pandas", "spark")


def verify_source(source: Path, evidence: Path) -> dict:
    accepted = json.loads(evidence.read_text(encoding="utf-8"))
    if (accepted.get("accepted") is not True or accepted.get("rows") != EXPECTED_ORIGINAL_ROWS
            or accepted.get("class_counts", {}).get("1") != EXPECTED_ORIGINAL_FRAUD
            or accepted.get("csv_sha256") != sha256_file(source)):
        raise ValueError("CSV does not match accepted original Phase 1 evidence")
    return accepted


def file_bytes(path: Path, pattern: str) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(part.stat().st_size for part in path.rglob(pattern))


def run_scale(args, scale: int, source: dict) -> dict:
    with TemporaryDirectory(prefix=f"scale-{scale}-", dir=args.work_dir) as directory:
        directory = Path(directory)
        inputs = directory / "input"
        prepare_input(args.input, inputs, scale)
        input_bytes = file_bytes(inputs, "*.csv")
        results = {name: [] for name in ENGINES}
        reference = None
        for repeat in range(1, args.repeats + 1):
            # Alternate order to reduce systematic filesystem-cache bias.
            order = ENGINES if repeat % 2 else tuple(reversed(ENGINES))
            for engine in order:
                print(f"{scale}x · repeat {repeat} · {engine}", flush=True)
                output = directory / f"{engine}.parquet"
                metrics = directory / "metrics.json"
                subprocess.run([
                    sys.executable, "-m", "fraud_benchmarks.worker",
                    engine, str(inputs), str(output), str(metrics), "--master", args.master,
                    "--driver-memory", args.driver_memory,
                ], check=True, env={**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"})
                audit = audit_output(output, source["rows"], source["class_counts"]["1"], scale)
                if reference is None:
                    reference = audit
                elif audit != reference:
                    raise ValueError(f"Parquet aggregate mismatch at {scale}x ({engine})")
                results[engine].append({
                    **json.loads(metrics.read_text(encoding="utf-8")),
                    "repeat": repeat,
                    "position": order.index(engine) + 1,
                    "output_bytes": file_bytes(output, "*.parquet"),
                })
                if args.keep_parquet and repeat == args.repeats:
                    output.rename(args.work_dir / f"{directory.name}-{engine}.parquet")
                elif output.is_dir():
                    import shutil

                    shutil.rmtree(output)
                else:
                    output.unlink()

    summary = {}
    for engine, runs in results.items():
        elapsed = [run["elapsed_seconds"] for run in runs]
        summary[engine] = {
            "median_elapsed_seconds": statistics.median(elapsed),
            "min_elapsed_seconds": min(elapsed),
            "max_elapsed_seconds": max(elapsed),
            "sample_stdev_seconds": statistics.stdev(elapsed) if len(elapsed) > 1 else None,
        }
    return {
        "scale": scale, "input_csv_bytes": input_bytes, "parity": reference,
        "measurements": results, "summary": summary,
    }


def main() -> None:
    config = yaml.safe_load((ROOT / "configs/experiment.yaml").read_text())["benchmark"]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/raw/creditcard.csv")
    parser.add_argument("--phase1-evidence", type=Path,
                        default=ROOT / "artifacts/phase_01/acceptance.json")
    parser.add_argument("--scales", type=int, nargs="+", choices=config["scales"],
                        default=config["scales"])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--master", default="local[2]")
    parser.add_argument("--driver-memory", default="2g")
    parser.add_argument("--work-dir", type=Path, default=ROOT / "data/benchmark")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/phase_03/benchmark.json")
    parser.add_argument("--keep-parquet", action="store_true")
    args = parser.parse_args()
    if args.repeats < 1 or len(args.scales) != len(set(args.scales)):
        parser.error("Use positive repeats and unique scales")
    args.work_dir = args.work_dir.resolve()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.unlink(missing_ok=True)
    source = verify_source(args.input, args.phase1_evidence)
    report = {
        "purpose": config["replicated_data_purpose"],
        "source_csv_sha256": source["csv_sha256"],
        "phase1_evidence_sha256": sha256_file(args.phase1_evidence),
        "source_csv_bytes": args.input.stat().st_size,
        "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "python": platform.python_version(),
        "versions": {name: version(name) for name in ("pandas", "pyarrow", "pyspark", "psutil")},
        "environment": {
            "platform": platform.platform(),
            "java": subprocess.check_output(["java", "-version"], stderr=subprocess.STDOUT,
                                            text=True).splitlines()[0],
            "available_logical_cpus": len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity")
            else os.cpu_count(),
            "host_memory_bytes": psutil.virtual_memory().total,
            "spark_master": args.master,
            "spark_driver_memory": args.driver_memory,
        },
        "config": {
            "scales": args.scales, "repeats": args.repeats, "pandas_batch_rows": PANDAS_BATCH_ROWS,
            "id_generation": "deterministic source row ordinal and replica ordinal",
            "timer_scope": "CSV read, hour feature, and Snappy Parquet write",
            "resource_scope": "sampled local driver process tree, every 100 ms",
        },
        "completed": False,
        "results": [],
    }
    for scale in args.scales:
        report["results"].append(run_scale(args, scale, source))
        report["completed"] = len(report["results"]) == len(args.scales)
        temporary = args.output.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        temporary.replace(args.output)
    print(args.output)


if __name__ == "__main__":
    main()
