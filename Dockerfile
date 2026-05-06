FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY motopay ./motopay
COPY apps ./apps
COPY alembic ./alembic
COPY alembic.ini ./

RUN pip install --no-cache-dir pip setuptools wheel \
    && pip install --no-cache-dir -e .

ENV PYTHONPATH=/app:/app/apps/streamlit_dashboard
