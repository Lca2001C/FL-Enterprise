import os
import sys
from pathlib import Path

# Permite `streamlit run apps/streamlit_dashboard/app.py` a partir da raiz do repositório
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import httpx
import streamlit as st

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

st.title("Painel")
st.caption("Use as páginas no menu lateral (Streamlit multipage).")
st.info("Páginas: Frota, Clientes, Contratos, Financeiro, Métricas e Cobranças.")
