from __future__ import annotations

import hashlib
import hmac
import re
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Literal
from zoneinfo import ZoneInfo

from motopay.config import get_settings
from motopay.config.mercadopago_credentials import (
    effective_mercadopago_access_token,
    effective_mercadopago_credentials_mode,
    effective_mercadopago_public_key,
    effective_mercadopago_webhook_secret,
)
from motopay.infrastructure.db.models import Operacao
from motopay.infrastructure.payments.mercadopago_sdk import (
    MercadoPagoApiError,
    RequestOptions,
    get_mercadopago_sdk,
    raise_for_sdk_error,
)
from motopay.infrastructure.payments.order_utils import (
    MercadoPagoOrderResult,
    ThreeDsInfo,
    is_order_paid,
    normalize_webhook_data_id,
    order_total_amount,
    parse_order_response,
)

__all__ = [
    "MercadoPagoClient",
    "MercadoPagoOrderResult",
    "ThreeDsInfo",
    "build_webhook_manifest",
    "compute_webhook_signature",
    "is_order_paid",
    "normalize_webhook_data_id",
    "order_total_amount",
    "parse_order_response",
    "verify_webhook_signature",
]


def payer_email_for_mercadopago(cliente_id: int) -> str:
    """E-mail do pagador aceito pelo Mercado Pago (sandbox exige @testuser.com)."""
    if effective_mercadopago_credentials_mode() == "test":
        return f"test_user_{cliente_id}@testuser.com"
    return f"cliente{cliente_id}@motopay.local"


def mercadopago_api_error_message(exc: MercadoPagoApiError) -> str:
    response = exc.response
    if isinstance(response, dict):
        errors = response.get("errors")
        if isinstance(errors, list) and errors:
            first = errors[0]
            if isinstance(first, dict) and first.get("message"):
                return str(first["message"])
        message = response.get("message")
        if message:
            return str(message)
    return str(exc)


def _normalize_cpf(cpf: str | None) -> str | None:
    if not cpf:
        return None
    digits = re.sub(r"\D", "", cpf)
    return digits if len(digits) == 11 else None


def _format_amount(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _pix_expiration_duration(due_date: date) -> str:
    tz = ZoneInfo(get_settings().app_timezone)
    now = datetime.now(tz)
    end = datetime.combine(due_date, time(23, 59, 59), tzinfo=tz)
    delta = end - now if end > now else timedelta(minutes=30)
    delta = max(delta, timedelta(minutes=30))
    delta = min(delta, timedelta(days=30))
    total_seconds = int(delta.total_seconds())
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"P{days}DT{hours}H{minutes}M{seconds}S"


def _panel_back_url() -> str:
    settings = get_settings()
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if origins:
        return origins[0].rstrip("/")
    return settings.api_public_base_url.rstrip("/")


def build_webhook_manifest(*, data_id: str, request_id: str, ts: str) -> str:
    return f"id:{data_id};request-id:{request_id};ts:{ts};"


def compute_webhook_signature(*, manifest: str, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), manifest.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest


def verify_webhook_signature(
    *,
    secret: str,
    x_signature: str,
    x_request_id: str,
    data_id: str,
) -> bool:
    if not secret.strip() or not x_signature.strip():
        return False

    parts: dict[str, str] = {}
    for segment in x_signature.split(","):
        segment = segment.strip()
        if "=" in segment:
            key, value = segment.split("=", 1)
            parts[key.strip()] = value.strip()

    ts = parts.get("ts", "")
    v1 = parts.get("v1", "")
    if not ts or not v1 or not x_request_id.strip() or not str(data_id).strip():
        return False

    manifest = build_webhook_manifest(
        data_id=normalize_webhook_data_id(str(data_id)),
        request_id=x_request_id.strip(),
        ts=ts,
    )
    expected = compute_webhook_signature(manifest=manifest, secret=secret.strip())
    return hmac.compare_digest(expected, v1)


class MercadoPagoClient:
    def __init__(self, *, access_token: str | None = None) -> None:
        token = (access_token or effective_mercadopago_access_token()).strip()
        if not token:
            raise ValueError("MERCADOPAGO_ACCESS_TOKEN não configurado")
        self._sdk = get_mercadopago_sdk(token)

    def _order_request_options(self, idempotency_key: str) -> RequestOptions:
        request_options = RequestOptions()
        request_options.custom_headers = {"x-idempotency-key": idempotency_key}
        return request_options

    def _build_payer(
        self,
        *,
        payer_email: str,
        payer_cpf: str | None = None,
        customer_id: str | None = None,
    ) -> dict[str, Any]:
        payer: dict[str, Any] = {"email": payer_email or "cliente@motopay.local"}
        if customer_id:
            payer["customer_id"] = customer_id
        cpf = _normalize_cpf(payer_cpf)
        if cpf:
            payer["identification"] = {"type": "CPF", "number": cpf}
        return payer

    def create_online_order(
        self,
        *,
        external_reference: str,
        value: Decimal,
        payer_email: str,
        payer_cpf: str | None = None,
        customer_id: str | None = None,
        payment_kind: Literal["pix", "credit_card", "debit_card"],
        payment_method_id: str | None = None,
        token: str | None = None,
        installments: int = 1,
        idempotency_key: str | None = None,
        pix_due_date: date | None = None,
    ) -> MercadoPagoOrderResult:
        amount = _format_amount(value)
        payer = self._build_payer(
            payer_email=payer_email,
            payer_cpf=payer_cpf,
            customer_id=customer_id,
        )

        if payment_kind == "pix":
            payment_method: dict[str, Any] = {
                "id": "pix",
                "type": "bank_transfer",
            }
            payment_entry: dict[str, Any] = {
                "amount": amount,
                "payment_method": payment_method,
            }
            if pix_due_date is not None:
                payment_entry["expiration_time"] = _pix_expiration_duration(pix_due_date)
        else:
            pm_id = (payment_method_id or "visa").strip()
            pm_type = "debit_card" if payment_kind == "debit_card" else "credit_card"
            if not token or not token.strip():
                raise ValueError("Token do cartão é obrigatório")
            payment_method = {
                "id": pm_id,
                "type": pm_type,
                "token": token.strip(),
                "installments": max(1, installments),
            }
            payment_entry = {
                "amount": amount,
                "payment_method": payment_method,
            }

        payload: dict[str, Any] = {
            "type": "online",
            "external_reference": external_reference,
            "total_amount": amount,
            "processing_mode": "automatic",
            "transactions": {"payments": [payment_entry]},
            "payer": payer,
        }

        key = idempotency_key or f"order-{external_reference}-{uuid.uuid4().hex[:16]}"
        result = self._sdk.order().create(
            payload,
            self._order_request_options(key),
        )
        raise_for_sdk_error(result)
        return parse_order_response(result["response"])

    def get_order(self, order_id: str) -> dict[str, Any]:
        result = self._sdk.order().get(order_id)
        raise_for_sdk_error(result)
        return result["response"]

    def cancel_order(self, order_id: str) -> None:
        result = self._sdk.order().cancel(order_id)
        raise_for_sdk_error(result)

    def create_preapproval(
        self,
        *,
        external_reference: str,
        value: Decimal,
        reason: str,
        payer_email: str,
    ) -> str:
        payload = {
            "reason": reason,
            "external_reference": external_reference,
            "status": "pending",
            "auto_recurring": {
                "frequency": 1,
                "frequency_type": "months",
                "transaction_amount": float(value),
                "currency_id": "BRL",
            },
            "payer_email": payer_email or "cliente@motopay.local",
            "back_url": _panel_back_url(),
        }
        result = self._sdk.preapproval().create(payload)
        raise_for_sdk_error(result)
        return str(result["response"]["id"])

    def ensure_customer(
        self,
        *,
        email: str,
        cpf: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        external_reference: str | None = None,
    ) -> str:
        search_filters: dict[str, Any] = {"email": email}
        search = self._sdk.customer().search(search_filters)
        raise_for_sdk_error(search)
        results = (search.get("response") or {}).get("results") or []
        if results:
            return str(results[0]["id"])

        payload: dict[str, Any] = {"email": email}
        if first_name:
            payload["first_name"] = first_name
        if last_name:
            payload["last_name"] = last_name
        if external_reference:
            payload["description"] = external_reference
        cpf_digits = _normalize_cpf(cpf)
        if cpf_digits:
            payload["identification"] = {"type": "CPF", "number": cpf_digits}

        created = self._sdk.customer().create(payload)
        raise_for_sdk_error(created)
        return str(created["response"]["id"])

    def save_card(self, customer_id: str, card_token: str) -> dict[str, Any]:
        result = self._sdk.card().create(customer_id, {"token": card_token})
        raise_for_sdk_error(result)
        return result["response"]

    def list_cards(self, customer_id: str) -> list[dict[str, Any]]:
        result = self._sdk.card().list_all(customer_id)
        raise_for_sdk_error(result)
        return list(result.get("response") or [])

    def delete_card(self, customer_id: str, card_id: str) -> None:
        result = self._sdk.card().delete(customer_id, card_id)
        raise_for_sdk_error(result)


def _parse_mp_card(card: dict[str, Any]) -> dict[str, Any]:
    pm = card.get("payment_method") or {}
    holder = card.get("cardholder") or {}
    return {
        "mp_card_id": str(card["id"]),
        "payment_method_id": str(pm.get("id") or card.get("payment_method_id") or "credit_card"),
        "last_four_digits": str(card.get("last_four_digits") or "0000")[-4:],
        "cardholder_name": holder.get("name"),
        "expiration_month": card.get("expiration_month"),
        "expiration_year": card.get("expiration_year"),
    }


def _operacao_has_any_mp_credential(op: Operacao) -> bool:
    return bool(
        (op.mercadopago_access_token or "").strip()
        or (op.mercadopago_public_key or "").strip()
        or (op.mercadopago_webhook_secret or "").strip()
    )


def operacao_mp_fields_complete(op: Operacao) -> bool:
    return bool(
        (op.mercadopago_access_token or "").strip()
        and (op.mercadopago_public_key or "").strip()
        and (op.mercadopago_webhook_secret or "").strip()
    )


def uses_operacao_mercadopago_credentials(op: Operacao | None) -> bool:
    return op is not None and _operacao_has_any_mp_credential(op)


def mp_token_for_operacao(op: Operacao | None) -> str:
    if uses_operacao_mercadopago_credentials(op):
        assert op is not None
        if not operacao_mp_fields_complete(op):
            return ""
        return op.mercadopago_access_token.strip()  # type: ignore[union-attr]
    if op and (op.mercadopago_access_token or "").strip():
        return op.mercadopago_access_token.strip()
    return effective_mercadopago_access_token()


def mp_public_key_for_operacao(op: Operacao | None) -> str:
    if uses_operacao_mercadopago_credentials(op):
        assert op is not None
        if not operacao_mp_fields_complete(op):
            return ""
        return op.mercadopago_public_key.strip()  # type: ignore[union-attr]
    if op and (op.mercadopago_public_key or "").strip():
        return op.mercadopago_public_key.strip()
    return effective_mercadopago_public_key()


def mp_webhook_secret_for_operacao(op: Operacao | None) -> str:
    if uses_operacao_mercadopago_credentials(op):
        assert op is not None
        if not operacao_mp_fields_complete(op):
            return ""
        return op.mercadopago_webhook_secret.strip()  # type: ignore[union-attr]
    if op and (op.mercadopago_webhook_secret or "").strip():
        return op.mercadopago_webhook_secret.strip()
    return effective_mercadopago_webhook_secret()


def mp_credentials_complete(op: Operacao | None) -> bool:
    if uses_operacao_mercadopago_credentials(op):
        assert op is not None
        return operacao_mp_fields_complete(op)
    return bool(
        effective_mercadopago_access_token()
        and effective_mercadopago_public_key()
        and effective_mercadopago_webhook_secret()
    )


def mp_credentials_source(op: Operacao | None) -> str:
    if op and operacao_mp_fields_complete(op):
        return "operacao"
    if effective_mercadopago_access_token():
        return "global"
    return "none"


def mp_configured_for_operacao(op: Operacao | None) -> bool:
    return bool(mp_token_for_operacao(op))


def mp_has_operacao_token(op: Operacao | None) -> bool:
    return bool(op and (op.mercadopago_access_token or "").strip())
