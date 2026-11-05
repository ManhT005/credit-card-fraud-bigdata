"""Deterministic synthetic data for contract tests; never original-source evidence."""

import numpy as np
import pandas as pd
import pytest

from fraud_detection.ingestion.profiling import FEATURE_COLUMNS


@pytest.fixture
def fraud_frame():
    rng = np.random.default_rng(42)
    rows = 240
    frame = pd.DataFrame(rng.normal(size=(rows, len(FEATURE_COLUMNS))), columns=FEATURE_COLUMNS)
    frame["Time"] = np.repeat(np.arange(rows//4), 4).astype(float)
    frame["Amount"] = rng.uniform(0, 100, size=rows)
    frame["Class"] = (np.arange(rows) % 12 == 0).astype(int)
    frame["V1"] += frame.Class * 3
    return frame
