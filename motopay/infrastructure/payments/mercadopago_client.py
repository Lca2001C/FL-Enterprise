from __future__ import annotations

import hashlib
import hmac
import re
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Literal

import httpx

from motopay.config import get_settings
from motopay.domain.enums import CicloCobranca
from motopay.config.mercadopago_credentials import (
    effective_mercadopago_access_token,
    effective_mercadopago_credentials_mode,
    effective_mercadopago_public_key,
    effective_mercadopago_webhook_secret,
)
from motopay.infrastructure.db.models import Cliente, Operacao
from motopay.infrastructure.payments.order_utils import (
    MercadoPagoOrderResult,
    parse_order_response,
)

__all__ = [
    "MercadoPagoApiError",
    "MercadoPagoClient",
    "MercadoPagoOrderResult",
    "build_webhook_manifest",
    "compute_webhook_signature",
    "mercadopago_api_error_message",
    "mp_configured_for_operacao",
    "mp_credentials_complete",
    "mp_credentials_source",
    "mp_has_operacao_token",
    "mp_public_key_for_operacao",
    "mp_token_for_operacao",
    "mp_webhook_secret_for_operacao",
    "payer_email_for_mercadopago",
    "uses_operacao_mercadopago_credentials",
    "verify_webhook_signature",
]


class MercadoPagoApiError(Exception):
    def __init__(self, status_code: int, message: str, response: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = response


def assert_payer_email_ready(cliente: Cliente) -> None:
    from motopay.domain.exceptions import ForbiddenError

    if effective_mercadopago_credentials_mode() == "test":
        return
    email = (cliente.email or "").strip()
    if not email or "@" not in email:
        raise ForbiddenError(
            "Cadastre o e-mail do cliente para pagamentos Mercado Pago em produção."
        )


def payer_email_for_mercadopago(cliente: Cliente | int) -> str:
    if isinstance(cliente, int):
        cliente_id = cliente
        email: str | None = None
    else:
        cliente_id = cliente.id
        email = (cliente.email or "").strip() or None

    if effective_mercadopago_credentials_mode() == "test":
        return f"test_user_{cliente_id}@testuser.com"
    if email and "@" in email:
        return email.lower()
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


def build_webhook_manifest(*, data_id: str, request_id: str, ts: str) -> str:
    return f"id:{data_id};request-id:{request_id};ts:{ts};"


def compute_webhook_signature(*, manifest: str, secret: str) -> str:
    digest = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return digest


def verify_webhook_signature(
    *,
    secret: str,
    x_signature: str,
    x_request_id: str,
    data_id: str,
) -> bool:
    if not secret.strip():
        return False
    ts = ""
    v1 = ""
    for part in x_signature.split(","):
        part = part.strip()
        if part.startswith("ts="):
            ts = part[3:]
        elif part.startswith("v1="):
            v1 = part[3:]
    if not ts or not v1:
        return False
    from motopay.infrastructure.payments.order_utils import normalize_webhook_data_id

    manifest_id = normalize_webhook_data_id(data_id)
    manifest = build_webhook_manifest(data_id=manifest_id, request_id=x_request_id, ts=ts)
    expected = compute_webhook_signature(manifest=manifest, secret=secret)
    return hmac.compare_digest(expected, v1)


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


class MercadoPagoClient:
    def __init__(self, *, access_token: str | None = None) -> None:
        token = (access_token or effective_mercadopago_access_token()).strip()
        if not token:
            raise ValueError("MERCADOPAGO_ACCESS_TOKEN não configurado")
        self._token = token
        self._base = "https://api.mercadopago.com"

    def _headers(self, *, idempotency_key: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        r = httpx.request(
            method,
            f"{self._base}{path}",
            headers=self._headers(idempotency_key=idempotency_key),
            json=json,
            timeout=timeout,
        )
        if r.status_code >= 400:
            try:
                body = r.json()
            except Exception:
                body = r.text
            raise MercadoPagoApiError(r.status_code, r.text, body)
        return r.json()

    def create_online_order(
        self,
        *,
        external_reference: str,
        value: Decimal,
        payer_email: str,
        payer_cpf: str | None = None,
        payment_method_id: Literal["pix", "visa", "master", "elo", "amex", "debvisa", "debmaster"] | str = "pix",
        payment_method_type: Literal["bank_transfer", "credit_card", "debit_card"] = "bank_transfer",
        token: str | None = None,
        installments: int = 1,
        customer_id: str | None = None,
    ) -> MercadoPagoOrderResult:
        payer: dict[str, Any] = {"email": payer_email}
        cpf = _normalize_cpf(payer_cpf)
        if cpf:
            payer["identification"] = {"type": "CPF", "number": cpf}
        if customer_id:
            payer["customer_id"] = customer_id

        pm: dict[str, Any] = {"id": payment_method_id, "type": payment_method_type}
        if token:
            pm["token"] = token
        if payment_method_type == "credit_card":
            pm["installments"] = installments

        payload: dict[str, Any] = {
            "type": "online",
            "external_reference": external_reference,
            "processing_mode": "automatic",
            "total_amount": _format_amount(value),
            "transactions": {
                "payments": [
                    {
                        "amount": _format_amount(value),
                        "payment_method": pm,
                    }
                ]
            },
            "payer": payer,
        }
        data = self._request(
            "POST",
            "/v1/orders",
            json=payload,
            idempotency_key=str(uuid.uuid4()),
        )
        return parse_order_response(data)

    def get_order(self, order_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/orders/{order_id}", timeout=30.0)

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        return self._request("POST", f"/v1/orders/{order_id}/cancel", json={}, timeout=30.0)

    def get_payment(self, payment_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/payments/{payment_id}", timeout=30.0)

    def create_customer(self, *, email: str, first_name: str, cpf: str | None = None) -> str:
        payload: dict[str, Any] = {
            "email": email,
            "first_name": first_name[:255],
        }
        cpf_digits = _normalize_cpf(cpf)
        if cpf_digits:
            payload["identification"] = {"type": "CPF", "number": cpf_digits}
        data = self._request("POST", "/v1/customers", json=payload)
        return str(data["id"])

    def search_customer_by_email(self, email: str) -> str | None:
        data = self._request("GET", f"/v1/customers/search?email={email}", timeout=30.0)
        results = data.get("results") or []
        if results:
            return str(results[0]["id"])
        return None

    def get_or_create_customer(
        self, *, email: str, first_name: str, cpf: str | None = None
    ) -> str:
        existing = self.search_customer_by_email(email)
        if existing:
            return existing
        return self.create_customer(email=email, first_name=first_name, cpf=cpf)

    def save_card(self, *, customer_id: str, token: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/customers/{customer_id}/cards",
            json={"token": token},
        )

    def list_cards(self, customer_id: str) -> list[dict[str, Any]]:
        data = self._request("GET", f"/v1/customers/{customer_id}/cards", timeout=30.0)
        return list(data if isinstance(data, list) else [])

    def delete_card(self, *, customer_id: str, card_id: str) -> None:
        r = httpx.delete(
            f"{self._base}/v1/customers/{customer_id}/cards/{card_id}",
            headers=self._headers(),
            timeout=30.0,
        )
        if r.status_code >= 400:
            raise MercadoPagoApiError(r.status_code, r.text)

    @staticmethod
    def preapproval_frequency(ciclo: str) -> tuple[int, str]:
        if ciclo == CicloCobranca.SEMANAL.value:
            return 1, "weeks"
        return 1, "months"

    def create_preapproval(
        self,
        *,
        external_reference: str,
        value: Decimal,
        reason: str,
        payer_email: str,
        ciclo: str = CicloCobranca.MENSAL.value,
    ) -> dict[str, Any]:
        settings = get_settings()
        back_url = settings.api_public_base_url.rstrip("/")
        cors = [x.strip() for x in settings.cors_origins.split(",") if x.strip()]
        if cors and cors[0] != "*":
            back_url = cors[0]
        freq, freq_type = self.preapproval_frequency(ciclo)
        payload = {
            "reason": reason,
            "external_reference": external_reference,
            "auto_recurring": {
                "frequency": freq,
                "frequency_type": freq_type,
                "transaction_amount": float(value),
                "currency_id": "BRL",
            },
            "payer_email": payer_email,
            "back_url": back_url,
            "status": "pending",
        }
        return self._request("POST", "/preapproval", json=payload)

    def get_preapproval(self, preapproval_id: str) -> dict[str, Any]:
        return self._request("GET", f"/preapproval/{preapproval_id}", timeout=30.0)

    def cancel_preapproval(self, preapproval_id: str) -> dict[str, Any]:
        return self._request(
            "PUT",
            f"/preapproval/{preapproval_id}",
            json={"status": "cancelled"},
            timeout=30.0,
        )

    def update_preapproval_amount(
        self, preapproval_id: str, *, value: Decimal, ciclo: str
    ) -> dict[str, Any]:
        freq, freq_type = self.preapproval_frequency(ciclo)
        return self._request(
            "PUT",
            f"/preapproval/{preapproval_id}",
            json={
                "auto_recurring": {
                    "frequency": freq,
                    "frequency_type": freq_type,
                    "transaction_amount": float(value),
                    "currency_id": "BRL",
                }
            },
            timeout=30.0,
        )

    def get_chargeback(self, chargeback_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/chargebacks/{chargeback_id}", timeout=30.0)

    def create_refund(self, payment_id: str, *, amount: Decimal | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if amount is not None:
            payload["amount"] = float(amount)
        return self._request(
            "POST",
            f"/v1/payments/{payment_id}/refunds",
            json=payload if payload else {},
            idempotency_key=str(uuid.uuid4()),
            timeout=60.0,
        )

    @staticmethod
    def preapproval_init_point(data: dict[str, Any]) -> str | None:
        mode = effective_mercadopago_credentials_mode()
        if mode == "test":
            url = data.get("sandbox_init_point") or data.get("init_point")
        else:
            url = data.get("init_point") or data.get("sandbox_init_point")
        return str(url) if url else None


def exchange_oauth_code(*, code: str, redirect_uri: str) -> dict[str, Any]:
    settings = get_settings()
    client_id = settings.mercadopago_oauth_client_id.strip()
    client_secret = settings.mercadopago_oauth_client_secret.strip()
    if not client_id or not client_secret:
        raise ValueError("MERCADOPAGO_OAUTH_CLIENT_ID/SECRET não configurados")
    r = httpx.post(
        "https://api.mercadopago.com/oauth/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
        timeout=60.0,
    )
    if r.status_code >= 400:
        raise MercadoPagoApiError(r.status_code, r.text, r.json() if r.content else None)
    return r.json()


def refresh_oauth_token(*, refresh_token: str) -> dict[str, Any]:
    settings = get_settings()
    r = httpx.post(
        "https://api.mercadopago.com/oauth/token",
        data={
            "client_id": settings.mercadopago_oauth_client_id.strip(),
            "client_secret": settings.mercadopago_oauth_client_secret.strip(),
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=60.0,
    )
    if r.status_code >= 400:
        raise MercadoPagoApiError(r.status_code, r.text, r.json() if r.content else None)
    return r.json()


def build_oauth_authorization_url(*, state: str, redirect_uri: str) -> str:
    from urllib.parse import urlencode

    settings = get_settings()
    client_id = settings.mercadopago_oauth_client_id.strip()
    if not client_id:
        raise ValueError("MERCADOPAGO_OAUTH_CLIENT_ID não configurado")
    params = urlencode(
        {
            "client_id": client_id,
            "response_type": "code",
            "platform_id": "mp",
            "state": state,
            "redirect_uri": redirect_uri,
        }
    )
    return f"https://auth.mercadopago.com/authorization?{params}"


def parse_mp_card(card: dict[str, Any]) -> dict[str, Any]:
    return {
        "mp_card_id": str(card.get("id", "")),
        "payment_method_id": str(card.get("payment_method", {}).get("id", card.get("payment_method_id", ""))),
        "last_four_digits": str(card.get("last_four_digits", ""))[-4:],
        "cardholder_name": card.get("cardholder", {}).get("name") if isinstance(card.get("cardholder"), dict) else None,
        "expiration_month": card.get("expiration_month"),
        "expiration_year": card.get("expiration_year"),
    }
