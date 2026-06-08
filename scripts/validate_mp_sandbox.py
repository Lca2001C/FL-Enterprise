#!/usr/bin/env python3
"""Smoke test sandbox Mercado Pago: health + config/payments (opcional)."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def _get(url: str, headers: dict | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {"raw": body}
        return e.code, data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--token", default="", help="JWT para GET /api/v1/config/payments")
    args = parser.parse_args()
    base = args.api.rstrip("/")
    errors = 0

    code, data = _get(f"{base}/health")
    if code == 200 and data.get("status") == "ok":
        print("OK  /health")
    else:
        print(f"ERRO  /health -> {code} {data}")
        errors += 1

    if args.token:
        code, data = _get(
            f"{base}/api/v1/config/payments",
            headers={"Authorization": f"Bearer {args.token}"},
        )
        if code != 200:
            print(f"ERRO  /config/payments -> {code} {data}")
            errors += 1
        else:
            print(f"OK  mercadopago_credentials_complete={data.get('mercadopago_credentials_complete')}")
            print(f"    webhook_url={data.get('webhook_url')}")
            if not data.get("mercadopago_credentials_complete"):
                print("WARN  Configure os 3 campos MP em Ajustes ou .env")
    else:
        print("SKIP  /config/payments (passe --token apos login)")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
