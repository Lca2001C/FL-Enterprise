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

ENV PYTHONPATH=/app

CMD ["uvicorn", "motopay.interfaces.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
