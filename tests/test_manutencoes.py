from __future__ import annotations

from decimal import Decimal

from motopay.infrastructure.db.models import Financeiro, Manutencao, Moto, Usuario

from tests.conftest import auth_header, login


def _dono_headers(client, dono_user: Usuario) -> dict[str, str]:
    tokens = login(client, dono_user.email, "donodono")
    return auth_header(tokens["access_token"])


def _payload(moto_id: int, **overrides) -> dict:
    base = {
        "moto_id": moto_id,
        "tipo": "preventiva",
        "descricao": "Trocar óleo de motor",
        "causa": "prevencao",
        "valor": 40.00,
        "data": "2026-06-15",
        "km": 24215,
    }
    base.update(overrides)
    return base


def _criar(client, headers, moto_id: int, **overrides) -> dict:
    resp = client.post("/api/v1/manutencoes", json=_payload(moto_id, **overrides), headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Criação + integração com o financeiro
# ---------------------------------------------------------------------------


def test_criar_manutencao_preventiva_gera_despesa(
    client, db_session, dono_user: Usuario, moto_operacao_a: Moto
):
    headers = _dono_headers(client, dono_user)
    data = _criar(client, headers, moto_operacao_a.id)

    assert data["tipo"] == "preventiva"
    assert data["causa"] == "prevencao"
    assert data["moto_id"] == moto_operacao_a.id
    assert data["km"] == 24215
    assert data["moto_descricao"]
    assert data["financeiro_id"] is not None

    despesa = db_session.get(Financeiro, data["financeiro_id"])
    assert despesa is not None
    assert despesa.tipo == "despesa"
    assert despesa.categoria == "manutencao"
    assert despesa.valor == Decimal("40.00")
    assert str(despesa.data) == "2026-06-15"
    assert despesa.moto_id == moto_operacao_a.id
    assert despesa.operacao_id == moto_operacao_a.operacao_id
    assert "Trocar óleo de motor" in despesa.descricao


def test_criar_manutencao_corretiva(client, dono_user: Usuario, moto_operacao_a: Moto):
    headers = _dono_headers(client, dono_user)
    data = _criar(
        client,
        headers,
        moto_operacao_a.id,
        tipo="corretiva",
        causa="desgaste",
        descricao="Pneu traseiro",
        valor=223.00,
        km=None,
    )
    assert data["tipo"] == "corretiva"
    assert data["causa"] == "desgaste"
    assert data["km"] is None


def test_admin_cria_manutencao_com_operacao_id(
    client, db_session, admin_user: Usuario, moto_operacao_a: Moto
):
    tokens = login(client, admin_user.email, "adminadmin")
    headers = auth_header(tokens["access_token"])
    resp = client.post(
        "/api/v1/manutencoes",
        params={"operacao_id": moto_operacao_a.operacao_id},
        json=_payload(moto_operacao_a.id),
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["operacao_id"] == moto_operacao_a.operacao_id


# ---------------------------------------------------------------------------
# Validações
# ---------------------------------------------------------------------------


def test_valor_zero_ou_negativo_rejeitado(client, dono_user: Usuario, moto_operacao_a: Moto):
    headers = _dono_headers(client, dono_user)
    for valor in (0, -10):
        resp = client.post(
            "/api/v1/manutencoes",
            json=_payload(moto_operacao_a.id, valor=valor),
            headers=headers,
        )
        assert resp.status_code == 422, resp.text


def test_descricao_vazia_rejeitada(client, dono_user: Usuario, moto_operacao_a: Moto):
    headers = _dono_headers(client, dono_user)
    resp = client.post(
        "/api/v1/manutencoes",
        json=_payload(moto_operacao_a.id, descricao=""),
        headers=headers,
    )
    assert resp.status_code == 422


def test_km_negativo_rejeitado(client, dono_user: Usuario, moto_operacao_a: Moto):
    headers = _dono_headers(client, dono_user)
    resp = client.post(
        "/api/v1/manutencoes",
        json=_payload(moto_operacao_a.id, km=-1),
        headers=headers,
    )
    assert resp.status_code == 422


def test_tipo_invalido_rejeitado(client, dono_user: Usuario, moto_operacao_a: Moto):
    headers = _dono_headers(client, dono_user)
    resp = client.post(
        "/api/v1/manutencoes",
        json=_payload(moto_operacao_a.id, tipo="revisao"),
        headers=headers,
    )
    assert resp.status_code == 422


def test_data_invalida_rejeitada(client, dono_user: Usuario, moto_operacao_a: Moto):
    headers = _dono_headers(client, dono_user)
    resp = client.post(
        "/api/v1/manutencoes",
        json=_payload(moto_operacao_a.id, data="15/06/2026"),
        headers=headers,
    )
    assert resp.status_code == 422


def test_moto_inexistente_rejeitada(client, dono_user: Usuario):
    headers = _dono_headers(client, dono_user)
    resp = client.post("/api/v1/manutencoes", json=_payload(999999), headers=headers)
    assert resp.status_code == 404


def test_moto_de_outra_operacao_rejeitada(
    client, dono_user: Usuario, moto_operacao_b: Moto
):
    headers = _dono_headers(client, dono_user)
    resp = client.post(
        "/api/v1/manutencoes", json=_payload(moto_operacao_b.id), headers=headers
    )
    assert resp.status_code == 404


def test_sem_autenticacao_rejeitado(client, moto_operacao_a: Moto):
    resp = client.post("/api/v1/manutencoes", json=_payload(moto_operacao_a.id))
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Edição sincroniza a despesa
# ---------------------------------------------------------------------------


def test_editar_manutencao_atualiza_despesa(
    client, db_session, dono_user: Usuario, moto_operacao_a: Moto
):
    headers = _dono_headers(client, dono_user)
    data = _criar(client, headers, moto_operacao_a.id)

    resp = client.patch(
        f"/api/v1/manutencoes/{data['id']}",
        json={"valor": 55.50, "data": "2026-06-20", "descricao": "Lona de freio traseiro"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["financeiro_id"] == data["financeiro_id"]

    despesa = db_session.get(Financeiro, data["financeiro_id"])
    assert despesa.valor == Decimal("55.50")
    assert str(despesa.data) == "2026-06-20"
    assert "Lona de freio traseiro" in despesa.descricao


def test_editar_manutencao_recria_despesa_se_vinculo_perdido(
    client, db_session, dono_user: Usuario, moto_operacao_a: Moto
):
    headers = _dono_headers(client, dono_user)
    data = _criar(client, headers, moto_operacao_a.id)

    # Simula perda do vínculo (ex.: linha removida por rotina externa).
    manut = db_session.get(Manutencao, data["id"])
    despesa_antiga = db_session.get(Financeiro, data["financeiro_id"])
    manut.financeiro_id = None
    db_session.delete(despesa_antiga)
    db_session.flush()

    resp = client.patch(
        f"/api/v1/manutencoes/{data['id']}", json={"valor": 99.90}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    novo_id = resp.json()["financeiro_id"]
    assert novo_id is not None
    nova = db_session.get(Financeiro, novo_id)
    assert nova.valor == Decimal("99.90")
    assert nova.categoria == "manutencao"


# ---------------------------------------------------------------------------
# Exclusão remove a despesa
# ---------------------------------------------------------------------------


def test_excluir_manutencao_remove_despesa(
    client, db_session, dono_user: Usuario, moto_operacao_a: Moto
):
    headers = _dono_headers(client, dono_user)
    data = _criar(client, headers, moto_operacao_a.id)

    resp = client.delete(f"/api/v1/manutencoes/{data['id']}", headers=headers)
    assert resp.status_code == 200

    assert db_session.get(Manutencao, data["id"]) is None
    assert db_session.get(Financeiro, data["financeiro_id"]) is None


# ---------------------------------------------------------------------------
# Despesa espelho protegida no financeiro
# ---------------------------------------------------------------------------


def test_despesa_de_manutencao_nao_pode_ser_editada_no_financeiro(
    client, dono_user: Usuario, moto_operacao_a: Moto
):
    headers = _dono_headers(client, dono_user)
    data = _criar(client, headers, moto_operacao_a.id)

    resp = client.patch(
        f"/api/v1/financeiro/{data['financeiro_id']}",
        json={"valor": 1.00},
        headers=headers,
    )
    assert resp.status_code == 409

    resp = client.delete(f"/api/v1/financeiro/{data['financeiro_id']}", headers=headers)
    assert resp.status_code == 409


def test_despesa_espelho_aparece_no_financeiro_com_categoria(
    client, dono_user: Usuario, moto_operacao_a: Moto
):
    headers = _dono_headers(client, dono_user)
    data = _criar(client, headers, moto_operacao_a.id)

    resp = client.get("/api/v1/financeiro", headers=headers)
    assert resp.status_code == 200
    itens = {i["id"]: i for i in resp.json()["items"]}
    espelho = itens[data["financeiro_id"]]
    assert espelho["categoria"] == "manutencao"
    assert espelho["tipo"] == "despesa"


# ---------------------------------------------------------------------------
# Multi-tenant
# ---------------------------------------------------------------------------


def test_dono_nao_acessa_manutencao_de_outra_operacao(
    client, db_session, dono_user: Usuario, operacao_b, moto_operacao_b: Moto
):
    manut = Manutencao(
        operacao_id=operacao_b.id,
        moto_id=moto_operacao_b.id,
        tipo="corretiva",
        descricao="Câmara de ar",
        causa="mau_uso",
        valor=Decimal("15.00"),
        data="2026-04-04",
    )
    db_session.add(manut)
    db_session.flush()

    headers = _dono_headers(client, dono_user)

    listagem = client.get("/api/v1/manutencoes", headers=headers)
    assert listagem.status_code == 200
    ids = [i["id"] for i in listagem.json()["items"]]
    assert manut.id not in ids

    patch = client.patch(
        f"/api/v1/manutencoes/{manut.id}", json={"valor": 1.00}, headers=headers
    )
    assert patch.status_code == 403

    delete = client.delete(f"/api/v1/manutencoes/{manut.id}", headers=headers)
    assert delete.status_code == 403


def test_resumo_isolado_por_operacao(
    client, db_session, dono_user: Usuario, moto_operacao_a: Moto, operacao_b, moto_operacao_b: Moto
):
    headers = _dono_headers(client, dono_user)
    _criar(client, headers, moto_operacao_a.id, valor=100.00)

    manut_b = Manutencao(
        operacao_id=operacao_b.id,
        moto_id=moto_operacao_b.id,
        tipo="corretiva",
        descricao="Pneu traseiro",
        causa="desgaste",
        valor=Decimal("999.00"),
        data="2026-06-01",
    )
    db_session.add(manut_b)
    db_session.flush()

    resp = client.get("/api/v1/manutencoes/resumo", headers=headers)
    assert resp.status_code == 200
    resumo = resp.json()
    assert Decimal(str(resumo["total_geral"])) == Decimal("100.00")
    assert resumo["quantidade"] == 1


# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------


def _seed_variado(client, headers, moto_id: int) -> None:
    _criar(client, headers, moto_id)  # preventiva/prevencao 40 em 2026-06-15
    _criar(
        client,
        headers,
        moto_id,
        tipo="corretiva",
        causa="desgaste",
        descricao="Pneu traseiro",
        valor=223.00,
        data="2026-01-22",
    )
    _criar(
        client,
        headers,
        moto_id,
        tipo="corretiva",
        causa="mau_uso",
        descricao="Desamassar roda",
        valor=55.00,
        data="2026-04-04",
    )


def test_filtro_por_tipo(client, dono_user: Usuario, moto_operacao_a: Moto):
    headers = _dono_headers(client, dono_user)
    _seed_variado(client, headers, moto_operacao_a.id)

    resp = client.get("/api/v1/manutencoes", params={"tipo": "corretiva"}, headers=headers)
    assert resp.status_code == 200
    itens = resp.json()["items"]
    assert len(itens) == 2
    assert all(i["tipo"] == "corretiva" for i in itens)


def test_filtro_por_causa(client, dono_user: Usuario, moto_operacao_a: Moto):
    headers = _dono_headers(client, dono_user)
    _seed_variado(client, headers, moto_operacao_a.id)

    resp = client.get("/api/v1/manutencoes", params={"causa": "mau_uso"}, headers=headers)
    assert resp.status_code == 200
    itens = resp.json()["items"]
    assert len(itens) == 1
    assert itens[0]["descricao"] == "Desamassar roda"


def test_filtro_por_periodo_bordas_inclusivas(
    client, dono_user: Usuario, moto_operacao_a: Moto
):
    headers = _dono_headers(client, dono_user)
    _seed_variado(client, headers, moto_operacao_a.id)

    resp = client.get(
        "/api/v1/manutencoes",
        params={"data_inicio": "2026-01-22", "data_fim": "2026-04-04"},
        headers=headers,
    )
    assert resp.status_code == 200
    datas = sorted(i["data"] for i in resp.json()["items"])
    assert datas == ["2026-01-22", "2026-04-04"]


def test_filtro_por_moto(client, db_session, dono_user: Usuario, operacao_a, moto_operacao_a: Moto):
    outra = Moto(
        operacao_id=operacao_a.id,
        placa="CCC3C33",
        modelo="Biz 125",
        status="disponivel",
        km=10,
    )
    db_session.add(outra)
    db_session.flush()

    headers = _dono_headers(client, dono_user)
    _criar(client, headers, moto_operacao_a.id)
    _criar(client, headers, outra.id, descricao="Lâmpadas", valor=40.00)

    resp = client.get("/api/v1/manutencoes", params={"moto_id": outra.id}, headers=headers)
    assert resp.status_code == 200
    itens = resp.json()["items"]
    assert len(itens) == 1
    assert itens[0]["moto_id"] == outra.id


def test_filtro_busca_descricao(client, dono_user: Usuario, moto_operacao_a: Moto):
    headers = _dono_headers(client, dono_user)
    _seed_variado(client, headers, moto_operacao_a.id)

    resp = client.get("/api/v1/manutencoes", params={"q": "pneu"}, headers=headers)
    assert resp.status_code == 200
    itens = resp.json()["items"]
    assert len(itens) == 1
    assert itens[0]["descricao"] == "Pneu traseiro"


# ---------------------------------------------------------------------------
# Resumo (totais para dashboard e PDF)
# ---------------------------------------------------------------------------


def test_resumo_totais_por_tipo_e_causa(client, dono_user: Usuario, moto_operacao_a: Moto):
    headers = _dono_headers(client, dono_user)
    _seed_variado(client, headers, moto_operacao_a.id)

    resp = client.get("/api/v1/manutencoes/resumo", headers=headers)
    assert resp.status_code == 200
    resumo = resp.json()
    assert Decimal(str(resumo["total_geral"])) == Decimal("318.00")
    assert resumo["quantidade"] == 3
    assert Decimal(str(resumo["total_preventiva"])) == Decimal("40.00")
    assert Decimal(str(resumo["total_corretiva"])) == Decimal("278.00")
    assert Decimal(str(resumo["por_causa"]["desgaste"])) == Decimal("223.00")
    assert len(resumo["por_moto"]) == 1
    assert resumo["por_moto"][0]["placa"] == moto_operacao_a.placa
    assert Decimal(str(resumo["por_moto"][0]["total"])) == Decimal("318.00")
    assert resumo["por_moto"][0]["quantidade"] == 3


def test_resumo_respeita_filtros(client, dono_user: Usuario, moto_operacao_a: Moto):
    headers = _dono_headers(client, dono_user)
    _seed_variado(client, headers, moto_operacao_a.id)

    resp = client.get(
        "/api/v1/manutencoes/resumo", params={"tipo": "corretiva"}, headers=headers
    )
    assert resp.status_code == 200
    resumo = resp.json()
    assert Decimal(str(resumo["total_geral"])) == Decimal("278.00")
    assert resumo["quantidade"] == 2


# ---------------------------------------------------------------------------
# Analytics: dashboard e ranking sem dupla contagem
# ---------------------------------------------------------------------------


def test_summary_inclui_manutencao_sem_dupla_contagem(
    client, dono_user: Usuario, moto_operacao_a: Moto
):
    headers = _dono_headers(client, dono_user)
    _criar(client, headers, moto_operacao_a.id, valor=100.00)

    receita = client.post(
        "/api/v1/financeiro",
        json={
            "tipo": "receita",
            "valor": 300.00,
            "descricao": "Aluguel",
            "data": "2026-06-15",
            "moto_id": moto_operacao_a.id,
        },
        headers=headers,
    )
    assert receita.status_code == 200, receita.text

    resp = client.get("/api/v1/analytics/summary", headers=headers)
    assert resp.status_code == 200
    s = resp.json()
    assert Decimal(str(s["receita_total"])) == Decimal("300.00")
    # A despesa espelho entra UMA vez em despesa_total; manutencao_total é recorte.
    assert Decimal(str(s["despesa_total"])) == Decimal("100.00")
    assert Decimal(str(s["manutencao_total"])) == Decimal("100.00")
    assert Decimal(str(s["lucro_liquido"])) == Decimal("200.00")


def test_ranking_motos_inclui_manutencao(client, dono_user: Usuario, moto_operacao_a: Moto):
    headers = _dono_headers(client, dono_user)
    _criar(client, headers, moto_operacao_a.id, valor=100.00, data="2026-06-15")

    resp = client.get(
        "/api/v1/analytics/motos/ranking",
        params={"data_inicio": "2026-06-01", "data_fim": "2026-06-30"},
        headers=headers,
    )
    assert resp.status_code == 200
    rows = {r["moto_id"]: r for r in resp.json()}
    row = rows[moto_operacao_a.id]
    assert Decimal(str(row["manutencao"])) == Decimal("100.00")
    assert Decimal(str(row["despesa"])) == Decimal("100.00")
    # Lucro considera a despesa espelho uma única vez: 0 - 100 = -100.
    assert Decimal(str(row["lucro_liquido"])) == Decimal("-100.00")


# ---------------------------------------------------------------------------
# Financeiro comum continua editável + validação de valor
# ---------------------------------------------------------------------------


def test_lancamento_comum_continua_editavel(client, dono_user: Usuario):
    headers = _dono_headers(client, dono_user)
    created = client.post(
        "/api/v1/financeiro",
        json={"tipo": "despesa", "valor": 50.00, "descricao": "Combustível", "data": "2026-06-10"},
        headers=headers,
    )
    assert created.status_code == 200, created.text
    fin_id = created.json()["id"]

    patched = client.patch(
        f"/api/v1/financeiro/{fin_id}", json={"valor": 60.00}, headers=headers
    )
    assert patched.status_code == 200

    deleted = client.delete(f"/api/v1/financeiro/{fin_id}", headers=headers)
    assert deleted.status_code == 200


def test_financeiro_valor_zero_rejeitado(client, dono_user: Usuario):
    headers = _dono_headers(client, dono_user)
    resp = client.post(
        "/api/v1/financeiro",
        json={"tipo": "despesa", "valor": 0, "descricao": "Inválido", "data": "2026-06-10"},
        headers=headers,
    )
    assert resp.status_code == 422
