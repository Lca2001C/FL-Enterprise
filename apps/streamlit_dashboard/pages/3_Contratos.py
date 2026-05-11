import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from refresh_helper import run_with_auto_refresh
from streamlit_api import get_json


def _page() -> None:
    st.title("Contratos")
    if not st.session_state.get("token"):
        st.stop()
    rows = get_json("/api/v1/contratos")
    st.dataframe(rows, use_container_width=True)


run_with_auto_refresh(_page)
