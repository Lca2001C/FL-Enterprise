#!/usr/bin/env bash
set -euo pipefail
docker compose up -d redis || docker-compose up -d redis
echo "Redis started. Configure .env e execute: uvicorn motopay.interfaces.api.main:app --reload"
