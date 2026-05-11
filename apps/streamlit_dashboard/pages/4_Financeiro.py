import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from refresh_helper import run_with_auto_refresh
from streamlit_api import get_json


def _page() -> None:
    st.title("Financeiro")
    if not st.session_state.get("token"):
        st.stop()
    rows = get_json("/api/v1/financeiro")
    if not rows:
        st.info("Nenhum lançamento.")
    else:
        df = pd.DataFrame(rows)
        df["data"] = pd.to_datetime(df["data"])
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)
        agg = df.groupby(["data", "tipo"])["valor"].sum().reset_index()
        agg_pivot = agg.pivot(index="data", columns="tipo", values="valor").fillna(0)
        fig = go.Figure()
        if "receita" in agg_pivot.columns:
            fig.add_trace(
                go.Scatter(
                    x=agg_pivot.index,
                    y=agg_pivot["receita"],
                    name="Receita",
                    mode="lines+markers",
                    line=dict(color="#27ae60"),
                )
            )
        if "despesa" in agg_pivot.columns:
            fig.add_trace(
                go.Scatter(
                    x=agg_pivot.index,
                    y=agg_pivot["despesa"],
                    name="Despesa",
                    mode="lines+markers",
                    line=dict(color="#e74c3c"),
                )
            )
        fig.update_layout(
            title="Evolução receita e despesa",
            xaxis_title="Data",
            yaxis_title="R$",
            height=400,
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.subheader("Lançamentos")
        st.dataframe(rows, use_container_width=True)


run_with_auto_refresh(_page)
