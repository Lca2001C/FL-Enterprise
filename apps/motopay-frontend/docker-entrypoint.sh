#!/bin/sh
set -eu

API_URL="${API_BASE_URL:-${VITE_API_BASE_URL:-}}"
CONFIG_PATH="/usr/share/nginx/html/runtime-config.json"

if [ -n "$API_URL" ] && [ "$API_URL" != "SAME_ORIGIN" ]; then
  escaped=$(printf '%s' "$API_URL" | sed 's/"/\\"/g')
  printf '{"apiBase":"%s"}\n' "$escaped" > "$CONFIG_PATH"
else
  printf '{"apiBase":""}\n' > "$CONFIG_PATH"
fi

exec nginx -g 'daemon off;'
