#!/usr/bin/env python3
"""Smoke checklist — valida API e comportamentos por aba do admin (stack local)."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

API = os.getenv("SMOKE_API_BASE", "http://localhost:8000").rstrip("/")
FRONT = os.getenv("SMOKE_FRONT_BASE", "http://localhost:5173").rstrip("/")
ADMIN_EMAIL = os.getenv("SMOKE_ADMIN_EMAIL", "admin@motopay.local")
ADMIN_PASS = os.getenv("SMOKE_ADMIN_PASS", "adminadmin")
DONO_EMAIL = os.getenv("SMOKE_DONO_EMAIL", "dono@motopay.local")
DONO_PASS = os.getenv("SMOKE_DONO_PASS", "donodono")


@dataclass
class Result:
    area: str
    check: str
    ok: bool
    detail: str = ""


results: list[Result] = []


def record(area: str, check: str, ok: bool, detail: str = "") -> None:
    results.append(Result(area, check, ok, detail))
    mark = "OK" if ok else "FAIL"
    line = f"[{mark}] {area} — {check}"
    if detail:
        line += f" ({detail})"
    print(line)


def request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    scope: int | None = None,
    body: dict | None = None,
    expect: int | tuple[int, ...] = 200,
) -> tuple[int, dict | list | str | None]:
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if scope is not None:
        headers["X-Operacao-Id"] = str(scope)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()
            code = resp.status
            try:
                parsed = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                parsed = raw
            return code, parsed
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = raw
        return e.code, parsed


def login(email: str, password: str) -> tuple[str | None, str]:
    code, data = request("POST", "/api/v1/auth/login", body={"email": email, "password": password})
    if code != 200 or not isinstance(data, dict):
        return None, f"HTTP {code}: {data}"
    return data.get("access_token"), "ok"


def get_me(token: str) -> dict | None:
    code, data = request("GET", "/api/v1/auth/me", token=token)
    if code == 200 and isinstance(data, dict):
        return data
    return None


def get_json(token: str, path: str, scope: int | None = None) -> tuple[int, dict | list | None]:
    code, data = request("GET", path, token=token, scope=scope)
    if isinstance(data, (dict, list)):
        return code, data
    return code, None


def main() -> int:
    print(f"Smoke checklist — API {API} | Front {FRONT}\n")

    # Infra
    code, health = request("GET", "/health")
    record("Infra", "API /health", code == 200 and health == {"status": "ok"}, str(health))

    try:
        with urllib.request.urlopen(FRONT, timeout=10) as r:
            front_ok = r.status == 200
    except Exception as e:
        front_ok = False
        record("Infra", "Frontend responde", False, str(e))
    else:
        record("Infra", "Frontend responde", front_ok, f"HTTP {r.status}")

    # Login — credencial inválida
    code, _ = request("POST", "/api/v1/auth/login", body={"email": "x@x.com", "password": "wrong"})
    record("Login", "Credencial inválida retorna erro", code in (401, 422, 400), f"HTTP {code}")

    admin_token, err = login(ADMIN_EMAIL, ADMIN_PASS)
    record("Login", "Admin autentica", admin_token is not None, err if not admin_token else "")

    dono_token, err = login(DONO_EMAIL, DONO_PASS)
    record("Login", "Dono autentica", dono_token is not None, err if not dono_token else "")

    if not admin_token or not dono_token:
        print("\nAbortando: login falhou.")
        return 1

    admin_me = get_me(admin_token)
    record("Login", "GET /auth/me admin", admin_me is not None and admin_me.get("tipo") == "admin")

    # Admin sem escopo — listagens devem responder (dados podem estar vazios ou globais)
    for path in [
        "/api/v1/motos?limit=1&offset=0",
        "/api/v1/clientes?limit=1&offset=0",
        "/api/v1/contratos?limit=1&offset=0",
        "/api/v1/cobrancas?limit=1&offset=0",
        "/api/v1/financeiro?limit=1&offset=0",
    ]:
        code, data = get_json(admin_token, path, scope=None)
        name = path.split("?")[0].split("/")[-1]
        ok = code == 200 and isinstance(data, dict) and "total" in data
        record("Admin sem escopo", f"GET {name}", ok, f"HTTP {code}")

    code, ops = get_json(admin_token, "/api/v1/operacoes")
    record("Admin sem escopo", "GET operacoes", code == 200 and isinstance(ops, list))
    scope_id = ops[0]["id"] if isinstance(ops, list) and ops else None

    if scope_id:
        code, motos = get_json(
            admin_token, "/api/v1/motos?limit=50&offset=0&q=test", scope=scope_id
        )
        record(
            "Admin com escopo",
            "Filtro motos q + escopo",
            code == 200 and isinstance(motos, dict),
            f"total={motos.get('total') if isinstance(motos, dict) else '?'}",
        )
        code, ct = get_json(
            admin_token,
            "/api/v1/contratos?limit=50&offset=0&inadimplente=true&cliente_id=1",
            scope=scope_id,
        )
        record(
            "Admin com escopo",
            "Contratos inadimplente+cliente_id",
            code == 200 and isinstance(ct, dict),
        )
    else:
        record("Admin com escopo", "Operação disponível para teste", False, "nenhuma operação")

    # Dashboard
    code, summary = get_json(dono_token, "/api/v1/analytics/summary")
    record("Dashboard", "Analytics summary", code == 200 and isinstance(summary, dict))

    code, activity = get_json(dono_token, "/api/v1/analytics/recent-activity")
    record("Dashboard", "Atividade recente", code == 200 and isinstance(activity, list))

    code, ct_total = get_json(dono_token, "/api/v1/contratos?limit=1&offset=0")
    record(
        "Dashboard",
        "totalContratos via limit=1",
        code == 200 and isinstance(ct_total, dict) and "total" in ct_total,
        f"total={ct_total.get('total') if isinstance(ct_total, dict) else '?'}",
    )

    code, inad = get_json(dono_token, "/api/v1/contratos?limit=50&offset=0&inadimplente=true")
    record(
        "Dashboard",
        "Inadimplentes server-side",
        code == 200 and isinstance(inad, dict) and "items" in inad,
        f"count={len(inad.get('items', [])) if isinstance(inad, dict) else 0}",
    )

    # Frota — filtros
    code, motos_f = get_json(dono_token, "/api/v1/motos?limit=50&offset=0&status=disponivel")
    record("Frota", "Filtro status server-side", code == 200 and isinstance(motos_f, dict))

    code, motos_q = get_json(dono_token, "/api/v1/motos?limit=50&offset=0&q=ABC")
    record("Frota", "Busca q server-side", code == 200 and isinstance(motos_q, dict))

    # Clientes
    code, cl_q = get_json(dono_token, "/api/v1/clientes?limit=50&offset=0&q=test")
    record("Clientes", "Busca q server-side", code == 200 and isinstance(cl_q, dict))

    # Cobranças
    code, cob = get_json(dono_token, "/api/v1/cobrancas?limit=50&offset=0&status=pendente")
    record("Cobranças", "Filtro status server-side", code == 200 and isinstance(cob, dict))

    code, ct_ativos = get_json(dono_token, "/api/v1/contratos?limit=200&offset=0&status=ativo")
    record("Cobranças", "Contratos ativos p/ modal", code == 200 and isinstance(ct_ativos, dict))

    # Contratos — abas
    for label, params in [
        ("todos", "limit=50&offset=0"),
        ("ativos", "limit=50&offset=0&status=ativo"),
        ("inadimplentes", "limit=50&offset=0&inadimplente=true"),
        ("com_promessa", "limit=50&offset=0&com_promessa=true"),
    ]:
        code, data = get_json(dono_token, f"/api/v1/contratos?{params}")
        record("Contratos", f"Aba {label}", code == 200 and isinstance(data, dict))

    # Métricas
    code, ranking = get_json(
        dono_token,
        "/api/v1/analytics/motos/ranking?data_inicio=2025-01-01&data_fim=2026-12-31",
    )
    record("Métricas", "Ranking motos", code == 200 and isinstance(ranking, list))

    # Financeiro
    code, fin = get_json(dono_token, "/api/v1/financeiro?limit=50&offset=0")
    record("Financeiro", "Listagem", code == 200 and isinstance(fin, dict))

    # Ajustes (dono)
    code, cfg = get_json(dono_token, "/api/v1/operacoes/me")
    record("Ajustes", "Config operação (dono)", code == 200 and isinstance(cfg, dict))

    # Admin usuários
    code, users = get_json(admin_token, "/api/v1/usuarios?limit=50&offset=0")
    record(
        "Admin Usuários", "Listagem", code == 200 and isinstance(users, dict) and "items" in users
    )

    # Paginação — offset > 0 quando total > PAGE_SIZE
    code, page0 = get_json(dono_token, "/api/v1/motos?limit=50&offset=0")
    if isinstance(page0, dict) and page0.get("total", 0) > 50:
        code, page1 = get_json(dono_token, "/api/v1/motos?limit=50&offset=50")
        record("Paginação", "Motos offset=50", code == 200 and isinstance(page1, dict))
    else:
        record("Paginação", "Motos offset=50", True, "skip (<51 motos)")

    # Tour helpers (lógica pura importada indiretamente — checar endpoints de auth/me para roles)
    record(
        "Tour",
        "Dono elegível (tipo=dono)",
        get_me(dono_token) is not None and get_me(dono_token).get("tipo") == "dono",
    )

    failed = [r for r in results if not r.ok]
    print(f"\n{'=' * 50}")
    print(f"Total: {len(results)} | OK: {len(results) - len(failed)} | FAIL: {len(failed)}")
    if failed:
        print("\nFalhas:")
        for r in failed:
            print(f"  - {r.area}: {r.check} — {r.detail}")
    print("\nItens UI-only (verificar no browser http://localhost:5173):")
    print("  - Banner tour: dismiss 'Depois' persiste; não reaparece após concluir")
    print("  - AdminScopeBanner visível sem escopo; some com escopo selecionado")
    print("  - Checklist dashboard (3 passos + botão Ir para Contratos)")
    print("  - Chip 'Filtrando cliente #id' em Contratos (Ver contratos em Clientes)")
    print("  - Paginação estilizada em Contratos; delete última linha da página")
    print("  - Reiniciar tour em Minha Conta -> volta ao dashboard")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
