"""Optional Phase 1 Spark smoke check (no training, no performance claims).

Usage: python scripts/spark_inspection.py --input data/raw/creditcard.csv
Requires pip install -e ".[spark]". Use Java supported by the Spark release.
"""

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/raw/creditcard.csv")
    args = parser.parse_args()
    path = Path(args.input).resolve()
    if not path.is_file():
        parser.error(f"Dataset not found: {path}")

    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F

    spark = SparkSession.builder.master("local[*]").appName("fraud-phase1-inspect").getOrCreate()
    try:
        df = spark.read.option("header", True).option("inferSchema", True).csv(str(path))
        print("Schema:")
        df.printSchema()
        print("Rows:", df.count())
        df.groupBy("Class").agg(F.count("*").alias("transactions")).orderBy("Class").show()
        print("Partitions:", df.rdd.getNumPartitions())
        print("This is a smoke check, NOT a benchmark.")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
