from __future__ import annotations

from datetime import date
from decimal import Decimal

from motopay.domain.enums import ContratoStatus, MotoStatus
from motopay.infrastructure.db.models import Cliente, Contrato, Moto, Usuario

from tests.conftest import auth_header, login


def test_list_motos_filter_status(client, admin_user: Usuario, moto_operacao_a: Moto):
    tokens = login(client, admin_user.email, "adminadmin")
    response = client.get(
        "/api/v1/motos",
        params={"status": MotoStatus.DISPONIVEL.value, "operacao_id": moto_operacao_a.operacao_id},
        headers=auth_header(tokens["access_token"]),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert all(item["status"] == MotoStatus.DISPONIVEL.value for item in data["items"])


def test_list_motos_filter_q(client, admin_user: Usuario, moto_operacao_a: Moto):
    tokens = login(client, admin_user.email, "adminadmin")
    response = client.get(
        "/api/v1/motos",
        params={"q": moto_operacao_a.placa[:4], "operacao_id": moto_operacao_a.operacao_id},
        headers=auth_header(tokens["access_token"]),
    )
    assert response.status_code == 200
    placas = {item["placa"] for item in response.json()["items"]}
    assert moto_operacao_a.placa in placas


def test_list_clientes_filter_q(client, admin_user: Usuario, operacao_a, db_session):
    cl = Cliente(
        operacao_id=operacao_a.id,
        nome="Joao Silva Teste",
        cpf="12345678901",
        telefone="11999999999",
        score=100,
    )
    db_session.add(cl)
    db_session.flush()
    tokens = login(client, admin_user.email, "adminadmin")
    response = client.get(
        "/api/v1/clientes",
        params={"q": "Joao Silva", "operacao_id": operacao_a.id},
        headers=auth_header(tokens["access_token"]),
    )
    assert response.status_code == 200
    nomes = [item["nome"] for item in response.json()["items"]]
    assert "Joao Silva Teste" in nomes


def test_list_contratos_filter_cliente_id(
    client, admin_user: Usuario, dono_user: Usuario, operacao_a, db_session, moto_operacao_a: Moto
):
    cl = Cliente(
        operacao_id=operacao_a.id,
        nome="Cliente Contrato",
        cpf="98765432100",
        telefone="11888888888",
        score=100,
    )
    db_session.add(cl)
    db_session.flush()
    ct = Contrato(
        operacao_id=operacao_a.id,
        cliente_id=cl.id,
        moto_id=moto_operacao_a.id,
        valor_recorrente=Decimal("500.00"),
        ciclo="mensal",
        status=ContratoStatus.ATIVO.value,
        data_inicio=date(2026, 1, 1),
        proximo_vencimento=date(2026, 2, 1),
    )
    db_session.add(ct)
    db_session.flush()
    tokens = login(client, admin_user.email, "adminadmin")
    response = client.get(
        "/api/v1/contratos",
        params={"cliente_id": cl.id, "operacao_id": operacao_a.id},
        headers=auth_header(tokens["access_token"]),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert all(item["cliente_id"] == cl.id for item in data["items"])
