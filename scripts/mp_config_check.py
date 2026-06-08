#!/usr/bin/env python3
"""Valida variáveis de ambiente Mercado Pago (sandbox/produção)."""

from __future__ import annotations

import os
import sys

# Permite rodar da raiz do repo sem instalar pacote
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motopay.config import get_settings
from motopay.config.mercadopago_credentials import (
    effective_mercadopago_access_token,
    effective_mercadopago_credentials_mode,
    effective_mercadopago_public_key,
    effective_mercadopago_webhook_secret,
)


def _ok(msg: str) -> None:
    print(f"  OK  {msg}")


def _warn(msg: str) -> None:
    print(f"  WARN  {msg}")


def _err(msg: str) -> None:
    print(f"  ERRO  {msg}")


def main() -> int:
    get_settings.cache_clear()
    s = get_settings()
    mode = effective_mercadopago_credentials_mode()
    errors = 0

    print("=== Mercado Pago — verificação de configuração ===\n")
    print(f"ENVIRONMENT={s.environment}")
    print(f"MERCADOPAGO_CREDENTIALS_MODE efetivo={mode}\n")

    token = effective_mercadopago_access_token()
    pk = effective_mercadopago_public_key()
    wh = effective_mercadopago_webhook_secret()

    if token:
        _ok(f"Access token efetivo configurado ({len(token)} chars)")
    else:
        _err("Access token efetivo ausente")
        errors += 1

    if pk:
        _ok("Public key efetiva configurada")
    else:
        _warn("Public key ausente — Payment Brick pode falhar até configurar em Ajustes")

    if wh:
        _ok("Webhook secret efetivo configurado")
    else:
        _warn("Webhook secret ausente — webhooks não validam HMAC (aceitos se secret vazio)")

    if s.api_public_base_url.startswith("http://localhost"):
        _warn(
            "API_PUBLIC_BASE_URL é localhost — Mercado Pago não alcança webhooks. "
            "Use ngrok e atualize API_PUBLIC_BASE_URL."
        )
    elif s.api_public_base_url.startswith("https://"):
        _ok(f"API_PUBLIC_BASE_URL={s.api_public_base_url}")
    else:
        _warn(f"API_PUBLIC_BASE_URL={s.api_public_base_url}")

    webhook_url = f"{s.api_public_base_url.rstrip('/')}/webhooks/mercadopago"
    print(f"\nURL do webhook (cadastre no painel MP, evento Order):\n  {webhook_url}\n")

    vite_pk = os.getenv("MERCADOPAGO_VITE_PUBLIC_KEY", "").strip() or os.getenv(
        "VITE_MERCADOPAGO_PUBLIC_KEY", ""
    ).strip()
    if vite_pk or pk:
        _ok("Public key disponível para frontend (env ou efetiva)")
    else:
        _warn("Sem VITE_MERCADOPAGO_PUBLIC_KEY / MERCADOPAGO_VITE_PUBLIC_KEY — SDK via API em runtime")

    print("\nProximos passos (credenciais por operacao):")
    print("  1. Painel MP: credenciais TEST por operacao")
    print("  2. Ajustes > Mercado Pago: token + public key + webhook secret")
    print("  3. docs/MERCADOPAGO_SETUP.md\n")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
