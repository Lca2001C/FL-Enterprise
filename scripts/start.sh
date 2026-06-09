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
USE_LAN=0
RUN_SEED=1
ACTION="up"

get_lan_ip() {
  local ip=""
  local script="$ROOT/scripts/get_lan_ip.py"
  local py_cmds=(py python3 python)
  if [[ -n "${MSYSTEM:-}" ]]; then
    py_cmds=(py python3 python)
    if command -v cygpath >/dev/null 2>&1; then
      script="$(cygpath -w "$script")"
    fi
  fi
  for py_cmd in "${py_cmds[@]}"; do
    if command -v "$py_cmd" >/dev/null 2>&1; then
      ip="$("$py_cmd" "$script" 2>/dev/null | tr -d '\r\n' || true)"
      if [[ -n "$ip" ]]; then
        break
      fi
    fi
  done
  if [[ -z "$ip" ]] && command -v ip >/dev/null 2>&1; then
    ip="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i = 1; i <= NF; i++) if ($i == "src") { print $(i + 1); exit }}' || true)"
  fi
  echo "$ip"
}

for arg in "$@"; do
  case "$arg" in
    --dev) USE_DEV=1 ;;
    --lan) USE_LAN=1 ;;
    --no-seed) RUN_SEED=0 ;;
    --down) ACTION="down" ;;
    -h|--help)
      cat <<'EOF'
Uso: ./scripts/start.sh [opções]

Opções:
  --dev      Usa docker-compose.dev.yml (hot reload no código Python)
  --lan      Expõe na rede local (CORS + build do front com IP da máquina)
  --no-seed  Não executa scripts/seed_admin.py após migrations
  --down     Para e remove containers (docker compose down)
  -h, --help Exibe esta ajuda

Após subir:
  Frontend  http://localhost:5173
  API       http://localhost:8000
  Com --lan   rebuilda o front apontando para o IP detectado automaticamente
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

ensure_docker_ready() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "Docker não encontrado no PATH. Instale o Docker Desktop:" >&2
    echo "  https://docs.docker.com/desktop/setup/install/windows-install/" >&2
    exit 1
  fi
  if docker info >/dev/null 2>&1; then
    return 0
  fi
  echo "Docker Desktop não está em execução." >&2
  if [[ "$(uname -s 2>/dev/null || true)" == MINGW* ]] || [[ -n "${MSYSTEM:-}" ]]; then
    local docker_desktop="/c/Program Files/Docker/Docker/Docker Desktop.exe"
    if [[ -f "$docker_desktop" ]]; then
      echo "Iniciando Docker Desktop..." >&2
      if command -v cygpath >/dev/null 2>&1; then
        cmd.exe /c start "" "$(cygpath -w "$docker_desktop")" >/dev/null 2>&1 || true
      else
        cmd.exe /c start "" "C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe" >/dev/null 2>&1 || true
      fi
      local deadline=$((SECONDS + 180))
      while (( SECONDS < deadline )); do
        if docker info >/dev/null 2>&1 && docker ps >/dev/null 2>&1; then
          echo "Docker pronto." >&2
          return 0
        fi
        sleep 3
      done
    fi
  fi
  echo "Abra o Docker Desktop manualmente, aguarde ficar 'Running' e execute ./scripts/start.sh novamente." >&2
  echo "Se aparecer erro 500 no engine, reinicie o Docker Desktop ou rode: wsl --shutdown" >&2
  exit 1
}

ensure_port_free() {
  local port="$1"
  local label="$2"
  local compose_service="${3:-}"
  local container_port="${4:-$port}"

  if ! command -v netstat >/dev/null 2>&1; then
    return 0
  fi
  if ! netstat -ano 2>/dev/null | grep -qE "[.:]${port}[[:space:]].*LISTENING"; then
    return 0
  fi

  if [[ -n "$compose_service" ]]; then
    local mapped
    mapped=$("${COMPOSE[@]}" port "$compose_service" "$container_port" 2>/dev/null | sed 's/.*://' | tr -d '\r' || true)
    if [[ "$mapped" == "$port" ]]; then
      echo "Porta ${port} (${label}) já em uso pela stack MotoPay — continuando."
      return 0
    fi
  fi

  echo "Porta ${port} (${label}) já está em uso por outro processo — o Docker não pode subir." >&2
  echo "Encerre o processo local (ex.: uvicorn/python na porta ${port}) ou rode: ./scripts/start.sh --down" >&2
  echo "No PowerShell: Get-NetTCPConnection -LocalPort ${port} | Select OwningProcess" >&2
  exit 1
}

COMPOSE=(docker compose -f docker-compose.yml)
if [[ "$USE_DEV" -eq 1 ]]; then
  COMPOSE+=(-f docker-compose.dev.yml)
fi

ensure_docker_ready

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

LAN_IP=""
IS_PRODUCTION=0
if [[ -f .env ]] && grep -qE '^ENVIRONMENT=production' .env 2>/dev/null; then
  IS_PRODUCTION=1
fi

if [[ "$IS_PRODUCTION" -eq 0 ]]; then
  LAN_IP="$(get_lan_ip)"
  if [[ -n "$LAN_IP" ]]; then
    BASE_CORS="${CORS_ORIGINS:-}"
    if [[ -z "$BASE_CORS" ]] && [[ -f .env ]]; then
      BASE_CORS="$(grep -E '^CORS_ORIGINS=' .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r' || true)"
    fi
    if [[ -z "$BASE_CORS" ]]; then
      BASE_CORS="http://localhost:5173"
    fi
    export CORS_ORIGINS="${BASE_CORS},http://127.0.0.1:5173,http://${LAN_IP}:5173"
  fi
fi

if [[ "$USE_LAN" -eq 1 ]]; then
  if [[ -z "$LAN_IP" ]]; then
    LAN_IP="$(get_lan_ip)"
  fi
  if [[ -z "$LAN_IP" ]]; then
    echo "Aviso: não foi possível detectar o IP da rede local. Conecte-se ao Wi‑Fi e tente novamente." >&2
  else
    export VITE_API_BASE_URL="SAME_ORIGIN"
    echo "Modo rede local: abra http://${LAN_IP}:5173 no celular (mesma Wi‑Fi)."
    echo "Se não conectar, permita Docker/portas 5173 e 8000 no firewall do Windows."
  fi
fi

SERVICES=(db redis api worker beat frontend)

if grep -qE '^TELEGRAM_BOT_TOKEN=.+' .env 2>/dev/null; then
  SERVICES+=(bot)
  echo "TELEGRAM_BOT_TOKEN detectado — incluindo serviço bot."
else
  echo "TELEGRAM_BOT_TOKEN vazio — bot omitido."
fi

ensure_port_free 8000 "API" api 8000
ensure_port_free 5173 "Frontend" frontend 80

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

if [[ -z "$LAN_IP" ]] && [[ "$IS_PRODUCTION" -eq 0 ]]; then
  LAN_IP="$(get_lan_ip)"
fi

echo ""
echo "=============================================="
echo "  MotoPay em execução"
echo "=============================================="
echo ""
echo "  Link de acesso (este computador):"
echo "    http://localhost:5173"
echo ""
if [[ -n "$LAN_IP" ]]; then
  echo "  Link de acesso (celular / mesma Wi‑Fi):"
  echo "    http://${LAN_IP}:5173"
  echo ""
else
  echo "  Link de acesso (celular / mesma Wi‑Fi):"
  echo "    (IP não detectado — conecte-se ao Wi‑Fi e rode de novo)"
  echo ""
fi
echo "  API (documentação):"
echo "    http://localhost:8000/docs"
if [[ -n "$LAN_IP" ]]; then
  echo "    http://${LAN_IP}:8000/docs"
fi
echo ""
echo "  Credenciais padrão do seed:"
echo "    Admin  admin@motopay.local / adminadmin"
echo "    Dono   dono@motopay.local / donodono"
echo ""
echo "  Parar: ./scripts/start.sh --down"
echo "=============================================="
