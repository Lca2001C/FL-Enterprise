#!/usr/bin/env python3
"""Atualiza API_PUBLIC_BASE_URL no .env para testes de webhook com túnel (ngrok)."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"


def _set_env_key(content: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    line = f"{key}={value}"
    if pattern.search(content):
        return pattern.sub(line, content, count=1)
    return content.rstrip() + "\n" + line + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Configura API_PUBLIC_BASE_URL para webhook MP")
    parser.add_argument(
        "--url",
        required=True,
        help="URL HTTPS do túnel (ex. https://abc123.ngrok-free.app)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    url = args.url.strip().rstrip("/")
    if not url.startswith("https://"):
        print("ERRO: use URL HTTPS (ngrok/cloudflared).")
        return 1

    webhook = f"{url}/webhooks/mercadopago"
    print(f"API_PUBLIC_BASE_URL={url}")
    print(f"Webhook no painel MP (evento Order): {webhook}")

    if not ENV_PATH.is_file():
        print(f"AVISO: {ENV_PATH} não encontrado. Defina manualmente API_PUBLIC_BASE_URL.")
        return 0

    content = ENV_PATH.read_text(encoding="utf-8")
    new_content = _set_env_key(content, "API_PUBLIC_BASE_URL", url)
    if args.dry_run:
        print("(dry-run — .env não alterado)")
        return 0

    ENV_PATH.write_text(new_content, encoding="utf-8")
    print(f"Atualizado {ENV_PATH}")
    print("Reinicie a API: docker compose up -d api  ou  ./scripts/start.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
