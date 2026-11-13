"""Equivalent batch pandas and Spark ETL for indexed benchmark CSV inputs."""

from collections import Counter
from pathlib import Path

from fraud_detection.ingestion.profiling import EXPECTED_COLUMNS, FEATURE_COLUMNS

INDEX_COLUMNS = ("replica_id", "source_row_id")
INPUT_COLUMNS = (*INDEX_COLUMNS, *EXPECTED_COLUMNS)
OUTPUT_COLUMNS = (*INPUT_COLUMNS, "hour")
INTEGER_COLUMNS = (*INDEX_COLUMNS, "Class", "hour")
PANDAS_BATCH_ROWS = 50_000


def prepare_input(source: Path, target: Path, scale: int) -> None:
    """Add stable zero-based source and copy IDs without modifying any source field."""
    target.mkdir()
    with source.open("rb") as stream:
        header = stream.readline().rstrip(b"\r\n").decode("ascii")
        if tuple(header.split(",")) != EXPECTED_COLUMNS:
            raise ValueError("Original CSV header does not match the Phase 1 schema")
        offset = stream.tell()
        for replica in range(scale):
            stream.seek(offset)
            prefix = f"{replica},".encode()
            with (target / f"replica-{replica:03d}.csv").open("wb") as destination:
                destination.write((",".join(INPUT_COLUMNS) + "\n").encode())
                for row_id, line in enumerate(stream):
                    destination.write(prefix + str(row_id).encode() + b"," + line)


def pandas_etl(source: Path, output: Path) -> int:
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq

    schema = pa.schema([
        (name, pa.int64() if name in INTEGER_COLUMNS else pa.float64())
        for name in OUTPUT_COLUMNS
    ])
    types = {field.name: field.type.to_pandas_dtype() for field in schema if field.name != "hour"}
    files = sorted(source.glob("*.csv"))
    with pq.ParquetWriter(output, schema, compression="snappy", use_dictionary=False) as writer:
        for path in files:
            for batch in pd.read_csv(path, dtype=types, chunksize=PANDAS_BATCH_ROWS,
                                     float_precision="round_trip"):
                batch["hour"] = np.floor(batch["Time"] / 3600).astype("int64")
                writer.write_table(pa.Table.from_pandas(batch, schema=schema, preserve_index=False))
    return len(files)


def spark_etl(spark, source: Path, output: Path) -> int:
    from pyspark.sql import functions as F
    from pyspark.sql.types import DoubleType, LongType, StructField, StructType

    schema = StructType([
        StructField(name, DoubleType() if name in FEATURE_COLUMNS else LongType())
        for name in INPUT_COLUMNS
    ])
    frame = spark.read.csv(str(source), schema=schema, header=True, mode="FAILFAST",
                           enforceSchema=False)
    partitions = frame.rdd.getNumPartitions()
    frame = frame.withColumn("hour", F.floor(F.col("Time") / 3600))
    frame.write.mode("error").option("compression", "snappy").option(
        "parquet.enable.dictionary", "false"
    ).parquet(str(output))
    return partitions


def audit_output(output: Path, source_rows: int, fraud_rows: int, scale: int) -> dict:
    """Scan Parquet in bounded batches and verify schema, counts, and identity coverage."""
    import numpy as np
    import pyarrow as pa
    import pyarrow.dataset as ds

    dataset = ds.dataset(output, format="parquet")
    expected_types = [
        pa.int64() if name in INTEGER_COLUMNS else pa.float64() for name in OUTPUT_COLUMNS
    ]
    if dataset.schema.names != list(OUTPUT_COLUMNS) or dataset.schema.types != expected_types:
        raise ValueError("Parquet schema does not match the ETL contract")
    identities = np.zeros(source_rows * scale, dtype=bool)
    groups: Counter = Counter()
    for batch in dataset.to_batches(columns=[*INDEX_COLUMNS, "Class", "hour"]):
        replica, row, label, hour = (column.to_numpy() for column in batch.columns)
        if (not ((0 <= replica) & (replica < scale) & (0 <= row) & (row < source_rows)).all()
                or not ((label == 0) | (label == 1)).all()):
            raise ValueError("Parquet contains invalid identities or labels")
        index = replica * source_rows + row
        if len(np.unique(index)) != len(index) or identities[index].any():
            raise ValueError("Parquet contains duplicate benchmark identities")
        identities[index] = True
        keys, counts = np.unique(hour * 2 + label, return_counts=True)
        groups.update({(int(k // 2), int(k % 2)): int(n) for k, n in zip(keys, counts)})
    if not identities.all() or sum(n for (_, label), n in groups.items() if label) != fraud_rows * scale:
        raise ValueError("Parquet row or fraud count differs from the verified source scale")
    return {
        "rows": int(identities.size),
        "fraud_rows": fraud_rows * scale,
        "hour_class_counts": [[hour, label, n] for (hour, label), n in sorted(groups.items())],
    }
