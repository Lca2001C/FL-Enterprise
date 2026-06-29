#!/usr/bin/env python3
"""Garante chaves Mercado Pago no .env (sem sobrescrever valores existentes)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"
EXAMPLE = ROOT / ".env.example"

MP_KEYS = [
    "ENVIRONMENT",
    "MERCADOPAGO_CREDENTIALS_MODE",
    "MERCADOPAGO_ACCESS_TOKEN_TEST",
    "MERCADOPAGO_PUBLIC_KEY_TEST",
    "MERCADOPAGO_WEBHOOK_SECRET_TEST",
    "MERCADOPAGO_VITE_PUBLIC_KEY",
    "API_PUBLIC_BASE_URL",
    "CORS_ORIGINS",
    "VITE_API_BASE_URL",
]


def _parse_example_defaults() -> dict[str, str]:
    out: dict[str, str] = {}
    if not EXAMPLE.is_file():
        return out
    for line in EXAMPLE.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        if k in MP_KEYS:
            out[k] = v.strip()
    return out


def _has_key(content: str, key: str) -> bool:
    return re.search(rf"^{re.escape(key)}=", content, re.MULTILINE) is not None


def main() -> int:
    if not ENV.is_file():
        if EXAMPLE.is_file():
            ENV.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"Criado {ENV} a partir de .env.example")
        else:
            print("ERRO: .env e .env.example ausentes")
            return 1

    content = ENV.read_text(encoding="utf-8")
    defaults = _parse_example_defaults()
    added: list[str] = []

    for key in MP_KEYS:
        if not _has_key(content, key):
            val = defaults.get(key, "")
            if key == "MERCADOPAGO_VITE_PUBLIC_KEY" and not val:
                m = re.search(r"^MERCADOPAGO_PUBLIC_KEY_TEST=(.*)$", content, re.MULTILINE)
                if m and m.group(1).strip():
                    val = m.group(1).strip()
            content = content.rstrip() + f"\n{key}={val}\n"
            added.append(key)

    if added:
        ENV.write_text(content, encoding="utf-8")
        print("Chaves adicionadas ao .env:", ", ".join(added))
    else:
        print("Todas as chaves MP já existem no .env")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
