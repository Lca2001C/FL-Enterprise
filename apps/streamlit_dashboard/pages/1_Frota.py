import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from streamlit_api import get_json

st.title("Frota — motos")
if not st.session_state.get("token"):
    st.stop()
rows = get_json("/api/v1/motos")
st.dataframe(rows, use_container_width=True)
