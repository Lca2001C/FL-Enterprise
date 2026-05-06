#!/usr/bin/env bash
# Limpa proxy do ambiente e roda docker compose (útil quando proxy corporativo não resolve fora da VPN).
set -euo pipefail
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy
if [[ $# -eq 0 ]]; then
  docker compose up --build
else
  docker compose "$@"
fi
