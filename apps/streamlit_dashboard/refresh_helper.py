"""Auto-refresh periódico via st.fragment(run_every=...) quando STREAMLIT_REFRESH_SECONDS > 0."""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import timedelta
from typing import TypeVar

import streamlit as st

T = TypeVar("T", bound=Callable[..., None])


def run_with_auto_refresh(render: T) -> None:
    try:
        sec = int(os.getenv("STREAMLIT_REFRESH_SECONDS", "60"))
    except ValueError:
        sec = 60
    fragment = getattr(st, "fragment", None)
    if sec > 0 and fragment is not None:
        fragment(run_every=timedelta(seconds=sec))(render)()
    else:
        render()
