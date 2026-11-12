# Spark standalone on one Docker host

From the repository root, after acquiring and verifying the original CSV
with Phase 1, run:

```bash
mkdir -p artifacts/phase_03
docker compose -f infra/docker/compose.yaml up -d --build --scale worker=2 worker
docker compose -f infra/docker/compose.yaml run --rm --use-aliases benchmark \
  python scripts/phase_03_benchmark.py --master spark://master:7077 \
  --scales 1 --repeats 2 --output artifacts/phase_03/standalone.json
docker compose -f infra/docker/compose.yaml down
```

The master, two workers and transient benchmark client share the repository
at `/workspace`. This lets executors read the same staged files and write to
the same Parquet directory. Outputs created by the Compose process can be
owned by root on Linux. Keep each benchmark run on an idle host and store the
aggregate JSON alongside the local-mode report.
