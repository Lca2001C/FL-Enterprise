"""Testes do construtor de payload Mercado Pago (recomendações da doc oficial)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from motopay.infrastructure.payments.mp_payload_builder import (
    MercadoPagoDataError,
    build_additional_info,
    build_additional_info_payer,
    build_additional_info_shipments,
    build_items_for_contrato,
    build_mp_item,
    build_mp_payer,
    build_statement_descriptor,
    split_full_name,
    validate_amount,
    validate_cep,
    validate_cpf,
    validate_phone,
    validate_uf,
)

# --- split_full_name ---------------------------------------------------------


def test_split_full_name_basic():
    assert split_full_name("João da Silva") == ("João", "da Silva")


def test_split_full_name_single_word_uses_fallback_last():
    first, last = split_full_name("Beltrano")
    assert first == "Beltrano"
    assert last == "Mercadopago"  # MP exige first AND last


def test_split_full_name_override_wins():
    assert split_full_name("João Silva", sobrenome_override="Pereira") == (
        "João Silva",
        "Pereira",
    )


def test_split_full_name_empty_returns_defaults():
    assert split_full_name(None) == ("Cliente", "Mercadopago")


# --- statement_descriptor ----------------------------------------------------


def test_statement_descriptor_uppercase_no_accents_and_trim():
    out = build_statement_descriptor("São Paulo Veículos")
    assert out == "SAO PAULO VEI"  # 13 chars máx, sem acentos
    assert len(out) <= 13
    assert out == out.upper()


def test_statement_descriptor_fallback_when_blank():
    assert build_statement_descriptor("") == "MOTOPAY"
    assert build_statement_descriptor(None) == "MOTOPAY"


def test_statement_descriptor_filters_special_chars():
    out = build_statement_descriptor("Loja & Co. #1")
    assert out.startswith("LOJA")
    assert "&" not in out
    assert "#" not in out


# --- Validações --------------------------------------------------------------


def test_validate_cpf_ok():
    assert validate_cpf("123.456.789-09") == "12345678909"


def test_validate_cpf_rejects_short():
    with pytest.raises(MercadoPagoDataError):
        validate_cpf("123")


def test_validate_cpf_rejects_repeated():
    with pytest.raises(MercadoPagoDataError):
        validate_cpf("00000000000")


def test_validate_cep():
    assert validate_cep("01310-200") == "01310200"
    assert validate_cep("123") is None
    assert validate_cep(None) is None


def test_validate_uf():
    assert validate_uf("sp") == "SP"
    assert validate_uf("São") is None
    assert validate_uf("xx") == "XX"  # alfa de 2 chars passa formato


def test_validate_phone_with_55_prefix():
    assert validate_phone("+55 (11) 99876-5432") == ("11", "998765432")


def test_validate_phone_short_returns_none():
    assert validate_phone("123") is None


def test_validate_amount_positive():
    assert validate_amount("123.45") == Decimal("123.45")


def test_validate_amount_zero_raises():
    with pytest.raises(MercadoPagoDataError):
        validate_amount("0")


# --- build_mp_item / items ---------------------------------------------------


def test_build_mp_item_required_fields():
    item = build_mp_item(title="Locacao moto Honda", quantity=1, unit_price=Decimal("199.90"))
    assert item["title"] == "Locacao moto Honda"
    assert item["quantity"] == 1
    assert item["unit_price"] == "199.90"
    assert "category_id" not in item  # categoria é da Preferences API, não da Orders API v2
    assert "total_amount" not in item


def test_build_mp_item_rejects_zero_quantity():
    with pytest.raises(MercadoPagoDataError):
        build_mp_item(title="x", quantity=0, unit_price=Decimal("10"))


def test_build_mp_item_rejects_zero_price():
    with pytest.raises(MercadoPagoDataError):
        build_mp_item(title="x", quantity=1, unit_price=Decimal("0"))


def test_build_items_for_contrato_with_moto():
    moto = SimpleNamespace(modelo="Honda CG 160", placa="ABC1D23", tipo="moto")
    contrato = SimpleNamespace(id=42, moto=moto)
    items = build_items_for_contrato(contrato, moto=moto, total_value=Decimal("499.90"))
    assert len(items) == 1
    item = items[0]
    assert "Locacao" in item["title"]
    assert "Honda" in item["title"]
    assert "description" not in item  # removido — campo não documentado na Orders API v2
    assert "id" not in item
    assert "total_amount" not in item
    assert item["quantity"] == 1
    assert item["unit_price"] == "499.90"


def test_build_items_for_contrato_without_moto_fallback():
    items = build_items_for_contrato(None, moto=None, total_value=Decimal("150.00"))
    assert items[0]["title"] == "Locacao de veiculo"


# --- payer + additional_info -------------------------------------------------


def _fake_cliente(**overrides):
    base = SimpleNamespace(
        id=7,
        nome="Maria Souza Lima",
        sobrenome=None,
        cpf="529.982.247-25",  # CPF válido
        telefone="11998765432",
        email="maria@example.com",
        endereco_logradouro="Av Paulista",
        endereco_numero="1000",
        endereco_bairro="Bela Vista",
        endereco_cidade="São Paulo",
        endereco_estado="SP",
        endereco_cep="01310-200",
        created_at=datetime(2025, 1, 15, 10, 30, tzinfo=UTC),
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def test_build_mp_payer_full():
    cliente = _fake_cliente()
    payer = build_mp_payer(cliente)
    assert payer["first_name"] == "Maria"
    assert payer["last_name"] == "Souza Lima"
    assert payer["identification"] == {"type": "CPF", "number": "52998224725"}
    assert payer["email"] == "maria@example.com"


def test_build_mp_payer_email_required_raises_without_email():
    cliente = _fake_cliente(email=None)
    with pytest.raises(MercadoPagoDataError):
        build_mp_payer(cliente)


def test_build_mp_payer_email_fallback_when_email_missing():
    cliente = _fake_cliente(email=None)
    payer = build_mp_payer(cliente, fallback_email="cliente7@motopay.local")
    assert payer["email"] == "cliente7@motopay.local"


def test_additional_info_payer_has_registration_date():
    info = build_additional_info_payer(_fake_cliente())
    assert info["registration_date"].startswith("2025-01-15T10:30:00")


def test_additional_info_shipments_complete():
    shipments = build_additional_info_shipments(_fake_cliente())
    assert shipments is not None
    addr = shipments["receivers_address"]
    assert addr["zip_code"] == "01310200"
    assert addr["city_name"] == "São Paulo"
    assert addr["state_name"] == "SP"
    assert addr["street_name"] == "Av Paulista"
    assert addr["street_number"] == "1000"


def test_additional_info_shipments_none_when_incomplete():
    cliente = _fake_cliente(endereco_cep=None)
    assert build_additional_info_shipments(cliente) is None


def test_build_additional_info_empty_for_orders_api():
    info = build_additional_info(_fake_cliente())
    assert info == {}
