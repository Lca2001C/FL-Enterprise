import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from streamlit_api import get_json, post_json

st.title("Métricas")
if not st.session_state.get("token"):
    st.stop()

today = date.today()
col_a, col_b = st.columns(2)
with col_a:
    start = st.date_input("Início", value=today.replace(day=1), key="m_start")
with col_b:
    end = st.date_input("Fim", value=today, key="m_end")

# --- Cadastro rápido de despesa ---
with st.expander("Cadastrar despesa", expanded=False):
    st.caption("Registra uma despesa na operação atual (admin: informe **ID operação** na barra lateral se necessário).")
    d_val = st.number_input("Valor (R$)", min_value=0.01, value=50.0, format="%.2f", step=10.0, key="desp_val")
    d_desc = st.text_input("Descrição", placeholder="Ex.: óleo, pneu, revisão…", key="desp_desc")
    d_data = st.date_input("Data", value=today, key="desp_data")
    motos_opts = []
    try:
        motos_raw = get_json("/api/v1/motos")
        motos_opts = [(0, "— Nenhuma moto vinculada —")] + [
            (int(m["id"]), f'{m["placa"]} — {m["modelo"]}') for m in motos_raw
        ]
    except Exception:
        motos_opts = [(0, "— Erro ao carregar motos —")]
    d_moto_label = st.selectbox(
        "Moto (opcional, para custo por ativo)",
        options=range(len(motos_opts)),
        format_func=lambda i: motos_opts[i][1],
        key="desp_moto_sel",
    )
    d_moto_id = motos_opts[d_moto_label][0] if motos_opts else None
    if st.button("Salvar despesa", type="primary", key="btn_despesa"):
        if not (d_desc or "").strip():
            st.error("Informe uma descrição.")
        else:
            body = {
                "tipo": "despesa",
                "valor": float(d_val),
                "descricao": (d_desc or "").strip(),
                "data": d_data.isoformat(),
            }
            if d_moto_id and d_moto_id > 0:
                body["moto_id"] = d_moto_id
            try:
                post_json("/api/v1/financeiro", body)
                st.success("Despesa registrada.")
                st.rerun()
            except Exception as e:
                st.error(f"Não foi possível salvar: {e}")

st.divider()

# Resumo do período + ranking
try:
    summary = get_json("/api/v1/analytics/summary")
except Exception:
    summary = {}

try:
    rows = get_json(
        "/api/v1/analytics/motos/ranking",
        params={"data_inicio": start.isoformat(), "data_fim": end.isoformat()},
    )
except Exception:
    rows = []

if rows:
    df = pd.DataFrame(rows)
    df["label"] = df["placa"] + " — " + df["modelo"]
    total_rec = float(df["receita"].sum())
    total_desp = float(df["despesa"].sum())
    lucro_periodo = total_rec - total_desp

    k1, k2, k3 = st.columns(3)
    k1.metric("Receita no período (motos)", f"R$ {total_rec:,.2f}")
    k2.metric("Despesa no período (motos)", f"R$ {total_desp:,.2f}")
    k3.metric("Lucro agregado (ranking)", f"R$ {lucro_periodo:,.2f}")

    if total_rec > 0 or total_desp > 0:
        fig_pie = px.pie(
            pd.DataFrame({"Tipo": ["Receita", "Despesa"], "Valor": [total_rec, total_desp]}),
            values="Valor",
            names="Tipo",
            hole=0.4,
            color_discrete_map={"Receita": "#27ae60", "Despesa": "#e74c3c"},
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label+value")
        st.plotly_chart(fig_pie, use_container_width=True)

    df_top = df.nlargest(12, "lucro_liquido")
    fig_group = px.bar(
        df_top,
        x="label",
        y=["receita", "despesa"],
        barmode="group",
        labels={"value": "R$", "label": "Moto", "variable": ""},
        color_discrete_map={"receita": "#2ecc71", "despesa": "#e67e22"},
    )
    fig_group.update_layout(xaxis_tickangle=-30, height=460, legend_title_text="")
    st.plotly_chart(fig_group, use_container_width=True)

    df_plot = df.copy()
    df_plot["_tam"] = df_plot["lucro_liquido"].abs().clip(lower=5.0)
    fig_scatter = px.scatter(
        df_plot,
        x="despesa",
        y="receita",
        size="_tam",
        color="lucro_liquido",
        hover_name="label",
        color_continuous_scale="RdYlGn",
        labels={"despesa": "Despesa (R$)", "receita": "Receita (R$)", "lucro_liquido": "Lucro"},
    )
    fig_scatter.update_layout(height=420)
    st.plotly_chart(fig_scatter, use_container_width=True)

    df_sorted = df.sort_values("lucro_liquido", ascending=False)
    fig_bar = px.bar(
        df_sorted.head(20),
        x="label",
        y="lucro_liquido",
        color="prejuizo",
        labels={"lucro_liquido": "Lucro líquido (R$)", "label": "Moto", "prejuizo": "Prejuízo"},
        color_discrete_map={True: "#e74c3c", False: "#27ae60"},
    )
    fig_bar.update_layout(xaxis_tickangle=-35, height=480)
    st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("Tabela — ranking")
    st.dataframe(rows, use_container_width=True)
else:
    st.info("Sem dados de ranking no período. Defina **ID operação** (admin) ou cadastre lançamentos.")

# Evolução no período (todos os lançamentos financeiro)
try:
    fin_rows = get_json("/api/v1/financeiro")
except Exception:
    fin_rows = []

if fin_rows:
    df_f = pd.DataFrame(fin_rows)
    df_f["data"] = pd.to_datetime(df_f["data"])
    mask = (df_f["data"].dt.date >= start) & (df_f["data"].dt.date <= end)
    df_f = df_f.loc[mask]
    if not df_f.empty:
        st.subheader("Fluxo no período (lançamentos)")
        daily = df_f.groupby(["data", "tipo"])["valor"].sum().reset_index()
        daily["data"] = pd.to_datetime(daily["data"])
        fig_line = px.line(
            daily,
            x="data",
            y="valor",
            color="tipo",
            markers=True,
            labels={"valor": "R$", "data": "Data"},
            color_discrete_map={"receita": "#27ae60", "despesa": "#c0392b"},
        )
        fig_line.update_layout(height=380, hovermode="x unified")
        st.plotly_chart(fig_line, use_container_width=True)

if summary:
    st.subheader("Indicadores gerais (API summary)")
    c1, c2 = st.columns(2)
    with c1:
        fig_cob = go.Figure(
            data=[
                go.Bar(
                    x=["No prazo", "Atrasadas"],
                    y=[
                        int(summary.get("cobrancas_pendentes", 0)),
                        int(summary.get("cobrancas_atrasadas", 0)),
                    ],
                    marker_color=["#2ecc71", "#e74c3c"],
                )
            ]
        )
        fig_cob.update_layout(title="Cobranças", yaxis_title="Quantidade", height=320)
        st.plotly_chart(fig_cob, use_container_width=True)
    with c2:
        lucro_g = float(summary.get("lucro_liquido", 0))
        fig_gauge = go.Figure(
            go.Indicator(
                mode="number",
                value=lucro_g,
                title={"text": "Lucro líquido (geral)"},
                number={"prefix": "R$ ", "valueformat": ",.2f"},
            )
        )
        fig_gauge.update_layout(height=320)
        st.plotly_chart(fig_gauge, use_container_width=True)
