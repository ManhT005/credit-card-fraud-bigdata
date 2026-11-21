"""Locate repository data independently of a notebook kernel's working directory."""

from pathlib import Path


def find_project_root(start: str | Path | None = None) -> Path:
    """Find the nearest project checkout above start (the current directory by default)."""
    location = Path.cwd() if start is None else Path(start).expanduser().resolve()
    for candidate in (location, *location.parents):
        if (candidate / "pyproject.toml").is_file() and (
            candidate / "src/fraud_detection"
        ).is_dir():
            return candidate
    raise FileNotFoundError("Run inside the credit-card-fraud-bigdata checkout")
