import os
import sys
from datetime import date
from pathlib import Path

# Permite `streamlit run apps/streamlit_dashboard/app.py` a partir da raiz do repositório
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st

from streamlit_api import get_json

st.set_page_config(page_title="MotoPay Admin", layout="wide")

if "token" not in st.session_state:
    st.session_state.token = None
if "api_base" not in st.session_state:
    st.session_state.api_base = os.getenv("API_PUBLIC_BASE_URL", "http://localhost:8000")
if "operacao_id" not in st.session_state:
    st.session_state.operacao_id = 0

with st.sidebar:
    st.subheader("Sessão")
    st.text_input("URL da API", key="api_base")
    st.session_state.operacao_id = st.number_input(
        "ID operação (admin, opcional)", min_value=0, value=int(st.session_state.operacao_id or 0)
    )
    if st.session_state.token:
        if st.button("Sair"):
            st.session_state.token = None
            st.rerun()
    else:
        email = st.text_input("E-mail")
        password = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            try:
                r = httpx.post(
                    f"{str(st.session_state.api_base).rstrip('/')}/api/v1/auth/login",
                    json={"email": email, "password": password},
                    timeout=30.0,
                )
                r.raise_for_status()
                st.session_state.token = r.json()["access_token"]
                st.rerun()
            except Exception as e:
                st.error(f"Falha no login: {e}")

if not st.session_state.token:
    st.title("MotoPay Admin")
    st.warning("Faça login na barra lateral para continuar.")
    st.stop()

st.title("Painel executivo")
st.caption("Visão consolidada da operação. Ajuste a operação na barra lateral (admin).")

try:
    summary = get_json("/api/v1/analytics/summary")
except Exception as e:
    st.error(f"Não foi possível carregar o resumo: {e}")
    st.info("Use as páginas do menu lateral para detalhes.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Receita total", f"R$ {float(summary.get('receita_total', 0)):,.2f}")
c2.metric("Despesa total", f"R$ {float(summary.get('despesa_total', 0)):,.2f}")
lucro = float(summary.get("lucro_liquido", 0))
c3.metric("Lucro líquido", f"R$ {lucro:,.2f}")
c4.metric("Motos alugadas", int(summary.get("motos_ativas", 0)))

row2 = st.columns(3)
row2[0].metric("Inadimplentes (contratos)", int(summary.get("clientes_inadimplentes", 0)))
row2[1].metric("Cobranças no prazo", int(summary.get("cobrancas_pendentes", 0)))
row2[2].metric("Cobranças atrasadas", int(summary.get("cobrancas_atrasadas", 0)))

st.subheader("Distribuição receita × despesa")
rec = float(summary.get("receita_total", 0))
desp = float(summary.get("despesa_total", 0))
if rec > 0 or desp > 0:
    df_fin = pd.DataFrame({"Tipo": ["Receita", "Despesa"], "Valor": [rec, desp]})
    fig_pie = px.pie(
        df_fin,
        values="Valor",
        names="Tipo",
        hole=0.45,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_pie.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig_pie, use_container_width=True)
else:
    st.info("Sem lançamentos financeiros para exibir no gráfico.")

st.subheader("Status das cobranças")
df_cob = pd.DataFrame(
    {
        "Status": ["No prazo", "Atrasadas", "Total"],
        "Quantidade": [
            int(summary.get("cobrancas_pendentes", 0)),
            int(summary.get("cobrancas_atrasadas", 0)),
            int(summary.get("total_cobrancas", 0)),
        ],
    }
)
fig_bar = px.bar(
    df_cob[df_cob["Status"] != "Total"],
    x="Status",
    y="Quantidade",
    color="Status",
    text_auto=True,
    color_discrete_map={"No prazo": "#2ecc71", "Atrasadas": "#e74c3c"},
)
fig_bar.update_layout(showlegend=False, yaxis_title="Cobranças")
st.plotly_chart(fig_bar, use_container_width=True)

st.subheader("Lucro por moto (mês corrente)")
today = date.today()
start_mes = today.replace(day=1)
try:
    ranking = get_json(
        "/api/v1/analytics/motos/ranking",
        params={"data_inicio": start_mes.isoformat(), "data_fim": today.isoformat()},
    )
except Exception:
    ranking = []

if ranking:
    df_r = pd.DataFrame(ranking)
    df_r["label"] = df_r["placa"] + " — " + df_r["modelo"]
    df_top = df_r.nlargest(12, "lucro_liquido")
    fig_rank = px.bar(
        df_top,
        x="lucro_liquido",
        y="label",
        orientation="h",
        labels={"lucro_liquido": "Lucro líquido (R$)", "label": "Moto"},
        color="lucro_liquido",
        color_continuous_scale="RdYlGn",
    )
    fig_rank.update_layout(yaxis={"categoryorder": "total ascending"}, height=max(320, len(df_top) * 28))
    st.plotly_chart(fig_rank, use_container_width=True)
else:
    st.info("Sem dados de ranking no período ou filtre uma operação (admin).")

st.caption("Mais detalhes: páginas Frota, Clientes, Contratos, Financeiro, Métricas e Cobranças.")
