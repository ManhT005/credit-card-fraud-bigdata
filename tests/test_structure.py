"""Ensure the intended research directories exist."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_directories():
    required = [
        "configs",
        "data/raw",
        "data/processed",
        "data/benchmark",
        "docs",
        "notebooks",
        "dashboard",
        "infra/docker",
        "scripts",
        "reports",
        "src/fraud_detection",
    ]
    assert all((ROOT / part).is_dir() for part in required)
