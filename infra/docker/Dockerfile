FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends git openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /opt/phase3-requirements.txt
RUN python -m pip install --no-cache-dir -r /opt/phase3-requirements.txt
ENV SPARK_HOME=/usr/local/lib/python3.11/site-packages/pyspark \
    PYTHONPATH=/workspace/src \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /workspace
