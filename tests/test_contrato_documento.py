from __future__ import annotations

from datetime import date
from decimal import Decimal

from motopay.domain.enums import CicloCobranca, ContratoStatus, MotoStatus
from motopay.infrastructure.db.models import Cliente, Contrato, Moto, Usuario

from tests.conftest import auth_header, login


def test_download_contrato_documento(
    client, admin_user: Usuario, operacao_a, db_session
):
    cliente = Cliente(
        operacao_id=operacao_a.id,
        nome="Maria Locatária",
        cpf="52998224725",
        telefone="11988887777",
        score=100,
    )
    moto = Moto(
        operacao_id=operacao_a.id,
        placa="XYZ9Z99",
        modelo="Yamaha Factor 150",
        status=MotoStatus.ALUGADA.value,
        km=12500,
    )
    db_session.add_all([cliente, moto])
    db_session.flush()
    ct = Contrato(
        operacao_id=operacao_a.id,
        cliente_id=cliente.id,
        moto_id=moto.id,
        valor_recorrente=Decimal("350.00"),
        ciclo=CicloCobranca.MENSAL.value,
        status=ContratoStatus.ATIVO.value,
        data_inicio=date(2026, 1, 1),
        data_fim_vigencia=None,
        proximo_vencimento=date(2026, 6, 1),
    )
    db_session.add(ct)
    db_session.flush()

    tokens = login(client, admin_user.email, "adminadmin")
    response = client.get(
        f"/api/v1/contratos/{ct.id}/documento?operacao_id={operacao_a.id}",
        headers=auth_header(tokens["access_token"]),
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content[:4] == b"%PDF"
    assert "attachment" in response.headers.get("content-disposition", "")


def test_download_contrato_documento_not_found(client, admin_user: Usuario, operacao_a):
    tokens = login(client, admin_user.email, "adminadmin")
    response = client.get(
        f"/api/v1/contratos/999999/documento?operacao_id={operacao_a.id}",
        headers=auth_header(tokens["access_token"]),
    )
    assert response.status_code == 404
