"""Streamlit placeholder until fraud models and metrics are available."""

import streamlit as st

st.set_page_config(page_title="Credit Card Fraud | Big Data", layout="wide")
st.title("Credit Card Fraud Detection")
st.caption("Big Data Analytics · Research dashboard")
st.info(
    "Scaffold only. Data ingestion, training, prediction and fraud scoring "
    "will be added in later phases."
)
st.subheader("Planned views")
st.write("Class balance · Precision–Recall curves · Risk thresholds · Spark benchmarks")
