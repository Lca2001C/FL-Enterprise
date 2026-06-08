"""Construtores de payload para Mercado Pago.

Implementa as recomendações da documentação oficial para melhoria da taxa
de aprovação de pagamentos:

- items[].title / quantity / unit_price / category_id
- payer.first_name / payer.last_name / payer.identification / payer.phone
- additional_info.payer.registration_date
- additional_info.shipments.receiver_address.{city_name,state_name,zip_code}
- statement_descriptor (nome no extrato do cartão)
- Device ID via header X-meli-session-id (passado pelo client HTTP)
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from motopay.infrastructure.db.models import Cliente, Contrato, Moto, Operacao

# --- Limites e constantes do Mercado Pago ------------------------------------

# statement_descriptor: 13 chars no Brasil, somente A-Z 0-9 e espaço
STATEMENT_DESCRIPTOR_MAX_LEN = 13

# Categorias válidas (MP categories list — locação de veículos)
DEFAULT_VEHICLE_RENTAL_CATEGORY = "vehicle_rental"


# --- Sanitização básica ------------------------------------------------------


def _digits_only(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\D+", "", value)


def _strip_accents(value: str) -> str:
    nfkd = unicodedata.normalize("NFKD", value)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _decimal(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    if value is None:
        return default
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return default


# --- Nome / sobrenome --------------------------------------------------------


def split_full_name(
    full_name: str | None, sobrenome_override: str | None = None
) -> tuple[str, str]:
    """Separa "João da Silva" em ("João", "da Silva").

    Se `sobrenome_override` (campo dedicado no cadastro) vier preenchido, ele
    tem prioridade. Caso contrário, divide pelo primeiro espaço.
    """
    nome = (full_name or "").strip()
    sobrenome = (sobrenome_override or "").strip()
    if sobrenome:
        return nome or sobrenome, sobrenome
    if not nome:
        return "Cliente", "Mercadopago"
    parts = nome.split()
    if len(parts) == 1:
        return parts[0], "Mercadopago"
    return parts[0], " ".join(parts[1:])


# --- Statement descriptor ----------------------------------------------------


def build_statement_descriptor(operacao_nome: str | None) -> str:
    raw = (operacao_nome or "MOTOPAY").strip().upper()
    sanitized = _strip_accents(raw)
    sanitized = re.sub(r"[^A-Z0-9 ]", "", sanitized).strip()
    if not sanitized:
        sanitized = "MOTOPAY"
    return sanitized[:STATEMENT_DESCRIPTOR_MAX_LEN]


# --- Validações para bloquear envio incompleto -------------------------------


class MercadoPagoDataError(ValueError):
    """Erro de dados de cliente/contrato incompletos para enviar ao MP."""


def validate_cpf(cpf: str | None) -> str:
    digits = _digits_only(cpf)
    if len(digits) != 11:
        raise MercadoPagoDataError("CPF inválido (deve ter 11 dígitos).")
    if digits == digits[0] * 11:
        raise MercadoPagoDataError("CPF inválido.")
    return digits


def validate_phone(phone: str | None) -> tuple[str, str] | None:
    digits = _digits_only(phone)
    if not digits:
        return None
    if len(digits) < 10 or len(digits) > 13:
        return None
    if digits.startswith("55") and len(digits) >= 12:
        digits = digits[2:]
    if len(digits) < 10:
        return None
    area = digits[:2]
    number = digits[2:]
    return area, number


def validate_cep(cep: str | None) -> str | None:
    digits = _digits_only(cep)
    if not digits:
        return None
    if len(digits) != 8:
        return None
    return digits


def validate_uf(state: str | None) -> str | None:
    s = (state or "").strip().upper()
    if len(s) != 2 or not s.isalpha():
        return None
    return s


def validate_amount(value: Any) -> Decimal:
    amount = _decimal(value)
    if amount <= 0:
        raise MercadoPagoDataError("Valor da cobrança deve ser maior que zero.")
    return amount


# --- Builders ----------------------------------------------------------------


def build_mp_payer(
    cliente: Cliente,
    *,
    require_email: bool = True,
    fallback_email: str | None = None,
) -> dict[str, Any]:
    """Monta o objeto payer com first_name, last_name, identification, phone."""
    first, last = split_full_name(cliente.nome, cliente.sobrenome)
    payer: dict[str, Any] = {
        "first_name": first[:255],
        "last_name": last[:255],
    }
    cpf = validate_cpf(cliente.cpf)
    payer["identification"] = {"type": "CPF", "number": cpf}

    email = (cliente.email or "").strip().lower() if cliente.email else ""
    if not email and fallback_email:
        email = fallback_email.strip().lower()
    if email:
        payer["email"] = email
    elif require_email:
        raise MercadoPagoDataError(
            "Cliente sem e-mail. Cadastre um e-mail para pagamentos Mercado Pago."
        )

    phone_parts = validate_phone(cliente.telefone)
    if phone_parts:
        area, number = phone_parts
        payer["phone"] = {"area_code": area, "number": number}
    return payer


def build_additional_info_payer(cliente: Cliente) -> dict[str, Any]:
    first, last = split_full_name(cliente.nome, cliente.sobrenome)
    info: dict[str, Any] = {
        "first_name": first[:255],
        "last_name": last[:255],
    }
    reg = getattr(cliente, "created_at", None)
    if isinstance(reg, datetime):
        if reg.tzinfo is None:
            reg = reg.replace(tzinfo=timezone.utc)
        info["registration_date"] = reg.isoformat(timespec="milliseconds")
    phone_parts = validate_phone(cliente.telefone)
    if phone_parts:
        area, number = phone_parts
        info["phone"] = {"area_code": area, "number": number}
    return info


def build_additional_info_shipments(cliente: Cliente) -> dict[str, Any] | None:
    cep = validate_cep(cliente.endereco_cep)
    city = (cliente.endereco_cidade or "").strip()
    state = validate_uf(cliente.endereco_estado)
    if not (cep and city and state):
        return None
    address: dict[str, Any] = {
        "zip_code": cep,
        "city_name": city[:128],
        "state_name": state,
    }
    if cliente.endereco_logradouro:
        address["street_name"] = cliente.endereco_logradouro[:255]
    if cliente.endereco_numero:
        digits = _digits_only(cliente.endereco_numero)
        address["street_number"] = digits or cliente.endereco_numero[:32]
    return {"receiver_address": address}


def build_mp_item(
    *,
    title: str,
    quantity: int,
    unit_price: Decimal,
    category_id: str = DEFAULT_VEHICLE_RENTAL_CATEGORY,
    description: str | None = None,
    item_id: str | None = None,
) -> dict[str, Any]:
    title_clean = (title or "").strip() or "Locacao de veiculo"
    if quantity < 1:
        raise MercadoPagoDataError("Quantidade do item deve ser maior que zero.")
    price = validate_amount(unit_price)
    item: dict[str, Any] = {
        "title": title_clean[:255],
        "quantity": quantity,
        "unit_price": float(price),
        "category_id": category_id,
        "currency_id": "BRL",
    }
    if description:
        item["description"] = description[:255]
    if item_id:
        item["id"] = item_id[:64]
    return item


def build_items_for_contrato(
    contrato: Contrato | None,
    *,
    moto: Moto | None = None,
    total_value: Decimal,
) -> list[dict[str, Any]]:
    """Gera lista items[] com base no contrato/moto da cobrança."""
    if contrato is None:
        return [
            build_mp_item(
                title="Locacao de veiculo",
                quantity=1,
                unit_price=total_value,
            )
        ]
    moto_obj = moto if moto is not None else getattr(contrato, "moto", None)
    if moto_obj is not None:
        tipo = (getattr(moto_obj, "tipo", "moto") or "moto").lower()
        modelo = getattr(moto_obj, "modelo", "") or ""
        placa = getattr(moto_obj, "placa", "") or ""
        title = f"Locacao {tipo} {modelo}".strip()
        title = re.sub(r"\s+", " ", title)
        description = f"Contrato #{contrato.id} - Placa {placa}" if placa else f"Contrato #{contrato.id}"
        item_id = f"contrato-{contrato.id}"
    else:
        title = "Locacao de veiculo"
        description = f"Contrato #{contrato.id}"
        item_id = f"contrato-{contrato.id}"
    return [
        build_mp_item(
            title=title,
            quantity=1,
            unit_price=total_value,
            description=description,
            item_id=item_id,
        )
    ]


def build_additional_info(
    cliente: Cliente,
    *,
    items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    info: dict[str, Any] = {"payer": build_additional_info_payer(cliente)}
    shipments = build_additional_info_shipments(cliente)
    if shipments:
        info["shipments"] = shipments
    if items:
        info["items"] = [
            {
                "id": it.get("id") or f"item-{i}",
                "title": it["title"],
                "description": it.get("description", it["title"]),
                "quantity": str(it["quantity"]),
                "unit_price": str(it["unit_price"]),
                "category_id": it.get("category_id", DEFAULT_VEHICLE_RENTAL_CATEGORY),
            }
            for i, it in enumerate(items, start=1)
        ]
    return info


# --- Helpers para preapproval (assinatura) ----------------------------------


def assert_subscription_ready(cliente: Cliente, contrato: Contrato) -> None:
    """Roda todas as validações antes de criar uma preapproval."""
    if not (cliente.nome or "").strip():
        raise MercadoPagoDataError("Nome do cliente é obrigatório.")
    validate_cpf(cliente.cpf)
    validate_amount(contrato.valor_recorrente)


__all__ = [
    "DEFAULT_VEHICLE_RENTAL_CATEGORY",
    "MercadoPagoDataError",
    "STATEMENT_DESCRIPTOR_MAX_LEN",
    "assert_subscription_ready",
    "build_additional_info",
    "build_additional_info_payer",
    "build_additional_info_shipments",
    "build_items_for_contrato",
    "build_mp_item",
    "build_mp_payer",
    "build_statement_descriptor",
    "split_full_name",
    "validate_amount",
    "validate_cep",
    "validate_cpf",
    "validate_phone",
    "validate_uf",
]
