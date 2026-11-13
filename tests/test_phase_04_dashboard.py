"""Smoke test the dashboard's published data and environment selector."""

from pathlib import Path

import pytest

st = pytest.importorskip("streamlit.testing.v1")

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_from_checked_in_evidence():
    app = st.AppTest.from_file(str(ROOT / "dashboard/app.py")).run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == ["Dataset", "Fraud detection", "ETL benchmark"]
    assert {metric.label: metric.value for metric in app.metric} == {
        "Original transactions": "284,807",
        "Fraud cases": "492",
        "Fraud prevalence": "0.173%",
        "Average precision": "0.840",
        "F₂": "0.810",
        "Precision": "0.767",
        "Recall": "0.821",
    }
    assert "Held-out test sealed" in app.info[0].value
    assert app.dataframe[1].value.values.tolist() == [[42652, 14], [10, 46]]
    assert app.dataframe[2].value.shape[0] == 11

    local = app.dataframe[3].value
    assert local["Scale"].unique().tolist() == ["1×", "10×", "100×"]
    assert local["Seconds"].tolist() == [2.526, 2.987, 22.813, 15.096, 235.817, 129.417]

    for mode, seconds in (
        ("CI · Spark local · 1×", [0.593, 3.044]),
        ("CI · Docker two workers · 1×", [0.890, 4.335]),
    ):
        app.selectbox[0].select(mode).run()
        assert not app.exception
        frame = app.dataframe[3].value
        assert frame["Scale"].tolist() == ["1×", "1×"]
        assert frame["Seconds"].tolist() == seconds
