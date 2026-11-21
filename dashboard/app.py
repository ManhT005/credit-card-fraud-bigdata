"""Read-only Streamlit dashboard for the verified research results."""

import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports/phase_03"
BENCHMARKS = {
    "Local · 1×–100×": "local_benchmark.json",
    "CI · Spark local · 1×": "ci_local_benchmark.json",
    "CI · Docker two workers · 1×": "ci_standalone_benchmark.json",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def show_dataset(evidence: dict) -> None:
    dataset = evidence["dataset"]
    fraud = dataset["class_counts"]["1"]
    rows = dataset["rows"]
    columns = st.columns(3)
    columns[0].metric("Original transactions", f"{rows:,}")
    columns[1].metric("Fraud cases", f"{fraud:,}")
    columns[2].metric("Fraud prevalence", f"{fraud / rows:.3%}")

    st.subheader("Chronological split")
    table = []
    for name in ("train", "validation", "test"):
        part = evidence["partitions"][name]
        table.append({
            "Partition": "Test · sealed" if name == "test" else name.title(),
            "Transactions": part["rows"],
            "Fraud": part["class_counts"]["1"],
            "Fraud rate": f'{part["class_counts"]["1"] / part["rows"]:.3%}',
        })
    st.dataframe(table, hide_index=True)
    st.caption(f"{dataset['duplicate_rows']:,} exact duplicate rows retained. "
               "Test counts are split inventory.")
    st.markdown("[OpenML 1597 · Dataset provenance](https://www.openml.org/d/1597)")


def show_validation(evidence: dict) -> None:
    candidate = evidence["candidate"]
    metrics = candidate["metrics"]
    st.subheader(f"{candidate['model_name']} · Chronological validation")
    st.info("Proposed candidate · Two independent sign-offs pending · Held-out test sealed")
    columns = st.columns(4)
    for column, (label, key) in zip(columns, (
        ("Average precision", "average_precision"), ("F₂", "f2"),
        ("Precision", "precision"), ("Recall", "recall"),
    )):
        column.metric(label, f"{metrics[key]:.3f}")

    curve = pd.DataFrame(candidate["pr_curve"]).reset_index(names="point")
    chart = alt.Chart(curve).mark_line(color="#007A72", strokeWidth=2.5).encode(
        x=alt.X("recall:Q", title="Recall", scale=alt.Scale(domain=[0, 1])),
        y=alt.Y("precision:Q", title="Precision", scale=alt.Scale(domain=[0, 1])),
        order="point:Q",
        tooltip=["recall:Q", "precision:Q"],
    ).properties(height=240)

    plot, operating_point = st.columns([3, 2])
    with plot:
        st.markdown("**Precision–recall curve**")
        st.altair_chart(chart)
    with operating_point:
        st.markdown("**Confusion matrix at the validation F₂ threshold**")
        st.caption(f"Threshold {metrics['threshold']:.6f} · Rows are actual classes")
        matrix = pd.DataFrame(metrics["confusion_matrix"],
                              index=["Actual legitimate", "Actual fraud"],
                              columns=["No alert", "Alert"])
        st.dataframe(matrix)
        st.write(f"{matrix.iloc[0, 1]:,} false alerts · {matrix.iloc[1, 0]:,} missed fraud cases")

    with st.expander("Compare all 11 validation runs"):
        comparison = pd.DataFrame(evidence["models"]).sort_values(
            ["average_precision", "f2", "model"], ascending=[False, False, True]
        )
        st.dataframe(comparison.round(4).rename(columns={
            "model": "Model", "average_precision": "AP", "precision": "Precision",
            "recall": "Recall", "f2": "F₂",
        }), hide_index=True)
    st.markdown(f"[Phase 2 evidence · Actions run]({evidence['source']['run_url']})")


def show_benchmark() -> None:
    mode = st.selectbox("Benchmark environment", list(BENCHMARKS))
    report = read_json(REPORTS / BENCHMARKS[mode])
    results = report["results"]
    repeats = report["config"]["repeats"]
    st.caption(f"Spark master `{report['environment']['spark_master']}` · "
               f"{repeats} run(s) per engine and scale · CSV → Snappy Parquet")

    scales = [f"{result['scale']}×" for result in results]
    rows = [
        {"Scale": f"{result['scale']}×", "Engine": engine,
         "Seconds": result["summary"][engine]["median_elapsed_seconds"],
         "Transactions": result["parity"]["rows"]}
        for result in results for engine in ("pandas", "spark")
    ]
    chart = alt.Chart(pd.DataFrame(rows)).mark_bar(cornerRadiusTopLeft=4,
                                                   cornerRadiusTopRight=4).encode(
        x=alt.X("Scale:N", sort=scales, title="Input scale"),
        xOffset=alt.XOffset("Engine:N", sort=["pandas", "spark"]),
        y=alt.Y("Seconds:Q", title="Median ETL time (seconds)"),
        color=alt.Color("Engine:N", scale=alt.Scale(
            domain=["pandas", "spark"], range=["#355777", "#007A72"]
        )),
        tooltip=["Scale:N", "Engine:N", "Transactions:Q",
                 alt.Tooltip("Seconds:Q", format=".3f")],
    ).properties(height=280)
    st.altair_chart(chart)
    st.dataframe(pd.DataFrame(rows).round({"Seconds": 3}), hide_index=True)
    st.caption("Replicated data is used exclusively for ETL measurement. "
               "Compare pandas and Spark within the selected environment.")
    st.markdown("[Phase 3 measurements and protocol]"
                "(https://github.com/ManhT005/credit-card-fraud-bigdata/blob/develop/"
                "docs/phase_03_results.md)")


st.set_page_config(page_title="Credit Card Fraud Research", layout="wide")
st.title("Credit Card Fraud Detection")
st.caption("OpenML 1597 · Model validation and ETL performance")
evidence = read_json(ROOT / "dashboard/phase_02_snapshot.json")
dataset_tab, validation_tab, benchmark_tab = st.tabs(
    ["Dataset", "Fraud detection", "ETL benchmark"]
)
with dataset_tab:
    show_dataset(evidence)
with validation_tab:
    show_validation(evidence)
with benchmark_tab:
    show_benchmark()
