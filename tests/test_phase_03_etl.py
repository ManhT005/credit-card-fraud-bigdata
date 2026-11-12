"""Verify that both engines preserve the input columns and build the same Parquet data."""

import csv

import pytest

from fraud_benchmarks.etl import (
    EXPECTED_COLUMNS,
    audit_output,
    pandas_etl,
    prepare_input,
    spark_etl,
)


def test_pandas_and_spark_match(tmp_path):
    pytest.importorskip("pyspark")
    import pyarrow.dataset as ds
    from pyspark.sql import SparkSession

    source = tmp_path / "original.csv"
    rows = [
        [0, *([0.25] * 28), 40.50, 0],
        [3599.5, *([-0.125] * 28), 0, 1],
        [3600, *([0.50] * 28), 100, 0],
        [3600, *([0.50] * 28), 100, 0],
    ]
    with source.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(EXPECTED_COLUMNS)
        writer.writerows(rows)

    inputs = tmp_path / "indexed"
    prepare_input(source, inputs, scale=2)
    pandas_output, spark_output = (tmp_path / name for name in ("pandas.parquet", "spark.parquet"))
    pandas_etl(inputs, pandas_output)
    spark = (SparkSession.builder.master("local[2]").appName("test-phase3")
             .config("spark.ui.enabled", "false").getOrCreate())
    try:
        spark_etl(spark, inputs, spark_output)
    finally:
        spark.stop()

    expected = {
        "rows": 8, "fraud_rows": 2, "hour_class_counts": [[0, 0, 2], [0, 1, 2], [1, 0, 4]],
    }
    assert audit_output(pandas_output, 4, 1, 2) == expected
    assert audit_output(spark_output, 4, 1, 2) == expected
    keys = [("replica_id", "ascending"), ("source_row_id", "ascending")]
    assert ds.dataset(pandas_output).to_table().sort_by(keys).equals(
        ds.dataset(spark_output).to_table().sort_by(keys)
    )
    with pytest.raises(ValueError, match="row or fraud count"):
        audit_output(spark_output, 5, 1, 2)
