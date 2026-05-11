import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from refresh_helper import run_with_auto_refresh
from streamlit_api import get_json, post_json


def _page() -> None:
    st.title("Cobranças")
    if not st.session_state.get("token"):
        st.stop()
    rows = get_json("/api/v1/cobrancas")
    st.dataframe(rows, use_container_width=True)
    st.subheader("Gerar Pix (Asaas)")
    cid = st.number_input("ID do contrato", min_value=1, step=1)
    if st.button("Criar cobrança Pix"):
        try:
            out = post_json("/api/v1/cobrancas/pix", {"contrato_id": int(cid)})
            st.json(out)
        except Exception as e:
            st.error(str(e))


run_with_auto_refresh(_page)
