#!/usr/bin/env bash
# Sobe a stack MotoPay via Docker Compose (migrations + seed incluídos).
# Uso: ./scripts/start.sh [--dev] [--no-seed] | ./scripts/start.sh --down
set -euo pipefail

unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Git Bash (MSYS) reescreve argumentos que parecem caminhos Unix ao chamar docker.exe
# (ex.: /app/alembic.ini vira caminho Windows inválido no container). O Alembic então
# lê config vazio e falha com: No 'script_location' key found in configuration.
if [[ -n "${MSYSTEM:-}" ]] || [[ -n "${MSYS:-}" ]]; then
  export MSYS2_ARG_CONV_EXCL='*'
fi

USE_DEV=0
RUN_SEED=1
ACTION="up"

for arg in "$@"; do
  case "$arg" in
    --dev) USE_DEV=1 ;;
    --no-seed) RUN_SEED=0 ;;
    --down) ACTION="down" ;;
    -h|--help)
      cat <<'EOF'
Uso: ./scripts/start.sh [opções]

Opções:
  --dev      Usa docker-compose.dev.yml (hot reload no código Python)
  --no-seed  Não executa scripts/seed_admin.py após migrations
  --down     Para e remove containers (docker compose down)
  -h, --help Exibe esta ajuda

Após subir:
  Frontend  http://localhost:5173
  API       http://localhost:8000
  Seed      admin@motopay.local / adminadmin
            dono@motopay.local / donodono
EOF
      exit 0
      ;;
    *)
      echo "Opção desconhecida: $arg (use --help)" >&2
      exit 1
      ;;
  esac
done

COMPOSE=(docker compose -f docker-compose.yml)
if [[ "$USE_DEV" -eq 1 ]]; then
  COMPOSE+=(-f docker-compose.dev.yml)
fi

if [[ "$ACTION" == "down" ]]; then
  "${COMPOSE[@]}" down
  echo "Stack parada."
  exit 0
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Criado .env a partir de .env.example."
  echo "Revise REDIS_URL=redis://redis:6379/0, VITE_API_BASE_URL e CORS_ORIGINS antes de produção."
fi

SERVICES=(db redis api worker beat frontend)

if grep -qE '^TELEGRAM_BOT_TOKEN=.+' .env 2>/dev/null; then
  SERVICES+=(bot)
  echo "TELEGRAM_BOT_TOKEN detectado — incluindo serviço bot."
else
  echo "TELEGRAM_BOT_TOKEN vazio — bot omitido."
fi

echo "Subindo serviços: ${SERVICES[*]}"
"${COMPOSE[@]}" up --build -d "${SERVICES[@]}"

echo "Aguardando API em http://localhost:8000/health ..."
deadline=$((SECONDS + 120))
until curl -sf http://localhost:8000/health >/dev/null 2>&1; do
  if (( SECONDS >= deadline )); then
    echo "Timeout: API não respondeu em 120s. Verifique: docker compose logs api" >&2
    exit 1
  fi
  sleep 2
done
echo "API pronta."

echo "Executando migrations..."
"${COMPOSE[@]}" exec -T api env PYTHONPATH=/usr/local/lib/python3.11/site-packages:/app \
  alembic -c /app/alembic.ini upgrade head

if [[ "$RUN_SEED" -eq 1 ]]; then
  echo "Executando seed..."
  "${COMPOSE[@]}" exec -T api python scripts/seed_admin.py
else
  echo "Seed omitido (--no-seed)."
fi

cat <<'EOF'

MotoPay em execução:
  Frontend  http://localhost:5173
  API       http://localhost:8000/docs

Credenciais padrão do seed (altere em produção):
  Admin  admin@motopay.local / adminadmin
  Dono   dono@motopay.local / donodono

Parar: ./scripts/start.sh --down
EOF
