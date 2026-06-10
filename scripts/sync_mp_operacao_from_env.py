#!/usr/bin/env python3
"""Sincroniza credenciais MP de teste do .env para uma operação (painel Ajustes / banco)."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


from motopay.infrastructure.db.models import Operacao  # noqa: E402
from motopay.infrastructure.db.session import SessionLocal  # noqa: E402


def _load_dotenv(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip()
    return out


def _is_placeholder_secret(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return True
    if all(ch in "•*." for ch in stripped):
        return True
    if re.fullmatch(r"[•\u2022]{8,}", stripped):
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync MP test credentials from .env to operacao")
    parser.add_argument("--operacao-id", type=int, default=3, help="ID da operação (padrão: 3 Teste)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    env = _load_dotenv(ROOT / ".env")

    def _get(key: str) -> str:
        return (os.getenv(key) or env.get(key, "")).strip()

    token = _get("MERCADOPAGO_ACCESS_TOKEN_TEST")
    public_key = _get("MERCADOPAGO_PUBLIC_KEY_TEST")
    webhook_secret = _get("MERCADOPAGO_WEBHOOK_SECRET_TEST")

    if _is_placeholder_secret(webhook_secret):
        webhook_secret = ""

    if not token or not public_key:
        print("ERRO: MERCADOPAGO_ACCESS_TOKEN_TEST e MERCADOPAGO_PUBLIC_KEY_TEST são obrigatórios no .env")
        return 1

    with SessionLocal() as db:
        op = db.get(Operacao, args.operacao_id)
        if not op:
            print(f"ERRO: operação {args.operacao_id} não encontrada")
            return 1

        print(f"Operação: [{op.id}] {op.nome}")
        print(f"  access_token: {'ok' if token else 'vazio'}")
        print(f"  public_key: {'ok' if public_key else 'vazio'}")
        print(f"  webhook_secret: {'ok' if webhook_secret else '(vazio — cadastre no painel MP e cole no .env)'}")

        if args.dry_run:
            print("(dry-run — banco não alterado)")
            return 0

        op.mercadopago_access_token = token
        op.mercadopago_public_key = public_key
        if webhook_secret:
            op.mercadopago_webhook_secret = webhook_secret
        elif op.mercadopago_webhook_secret and _is_placeholder_secret(op.mercadopago_webhook_secret):
            op.mercadopago_webhook_secret = None

        db.add(op)
        db.commit()
        print("Credenciais sincronizadas no banco (operacao).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
