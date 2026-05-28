FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY motopay ./motopay
COPY apps ./apps
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts

# Imagem usada por API, worker, beat e bot: não definir HEALTHCHECK aqui (worker/beat não expõem HTTP).
# Healthcheck da API: ver docker-compose.yml (serviço api).

RUN pip install --no-cache-dir "pip>=24.0,<25" "setuptools>=68" "wheel" \
    && pip install --no-cache-dir -e .

RUN useradd -m -u 1000 appuser \
    && mkdir -p /data/uploads \
    && chown -R appuser:appuser /app /data

ENV PYTHONPATH=/app

USER appuser

# Railway injeta PORT; desenvolvimento local sem PORT mantém 8000.
CMD ["sh", "-c", "exec uvicorn motopay.interfaces.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
