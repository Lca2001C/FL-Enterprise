"""Exclusão de cliente: bloqueia (409) quando há contratos, em vez de 500 (FK)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from motopay.domain.enums import CicloCobranca, CobrancaStatus, ContratoStatus
from motopay.infrastructure.db.models import Cliente, Contrato

from tests.conftest import auth_header, login


def _make_cliente(db_session, operacao_id: int, cpf: str = "11122233344") -> Cliente:
    c = Cliente(
        operacao_id=operacao_id,
        nome="Cliente Del",
        cpf=cpf,
        telefone="11999990000",
        email="del@example.com",
    )
    db_session.add(c)
    db_session.flush()
    return c


def test_delete_cliente_sem_contrato_ok(client, db_session, dono_user, operacao_a):
    c = _make_cliente(db_session, operacao_a.id)
    db_session.commit()
    token = login(client, "dono@test.local", "donodono")["access_token"]
    r = client.delete(f"/api/v1/clientes/{c.id}", headers=auth_header(token))
    assert r.status_code == 200, r.text


def test_delete_cliente_com_contrato_retorna_409(
    client, db_session, dono_user, operacao_a, moto_operacao_a
):
    c = _make_cliente(db_session, operacao_a.id, cpf="55566677788")
    ct = Contrato(
        operacao_id=operacao_a.id,
        cliente_id=c.id,
        moto_id=moto_operacao_a.id,
        valor_recorrente=Decimal("100"),
        ciclo=CicloCobranca.MENSAL.value,
        status=ContratoStatus.ATIVO.value,
        data_inicio=date(2025, 1, 1),
        proximo_vencimento=date(2025, 2, 1),
    )
    db_session.add(ct)
    db_session.commit()

    token = login(client, "dono@test.local", "donodono")["access_token"]
    r = client.delete(f"/api/v1/clientes/{c.id}", headers=auth_header(token))
    assert r.status_code == 409, r.text  # não 500
    assert "contrato" in r.json()["detail"].lower()


def test_delete_contrato_e_depois_cliente(
    client, db_session, dono_user, operacao_a, moto_operacao_a
):
    from motopay.infrastructure.db.models import Cobranca

    c = _make_cliente(db_session, operacao_a.id, cpf="99988877766")
    ct = Contrato(
        operacao_id=operacao_a.id,
        cliente_id=c.id,
        moto_id=moto_operacao_a.id,
        valor_recorrente=Decimal("150"),
        ciclo=CicloCobranca.MENSAL.value,
        status=ContratoStatus.ATIVO.value,
        data_inicio=date(2025, 1, 1),
        proximo_vencimento=date(2025, 2, 1),
    )
    db_session.add(ct)
    db_session.flush()
    cob = Cobranca(
        operacao_id=operacao_a.id,
        contrato_id=ct.id,
        valor=Decimal("150"),
        vencimento=date(2025, 2, 1),
        status=CobrancaStatus.PENDENTE.value,
    )
    db_session.add(cob)
    db_session.commit()
    ct_id, cob_id = ct.id, cob.id

    token = login(client, "dono@test.local", "donodono")["access_token"]
    # exclui o contrato (apaga cobranças) → 200
    r1 = client.delete(f"/api/v1/contratos/{ct_id}", headers=auth_header(token))
    assert r1.status_code == 200, r1.text
    assert db_session.get(Contrato, ct_id) is None
    assert db_session.get(Cobranca, cob_id) is None
    # agora o cliente pode ser excluído → 200
    r2 = client.delete(f"/api/v1/clientes/{c.id}", headers=auth_header(token))
    assert r2.status_code == 200, r2.text
