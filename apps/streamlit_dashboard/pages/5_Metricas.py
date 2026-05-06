import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from streamlit_api import get_json

st.title("Métricas — ranking de motos")
if not st.session_state.get("token"):
    st.stop()
today = date.today()
start = st.date_input("Início", value=today.replace(day=1))
end = st.date_input("Fim", value=today)
rows = get_json(
    "/api/v1/analytics/motos/ranking",
    params={"data_inicio": start.isoformat(), "data_fim": end.isoformat()},
)
st.dataframe(rows, use_container_width=True)
