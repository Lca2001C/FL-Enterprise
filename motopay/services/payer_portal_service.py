from __future__ import annotations

import secrets
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from motopay.config import get_settings
from motopay.config.mercadopago_credentials import effective_mercadopago_credentials_mode
from motopay.domain.enums import CobrancaStatus
from motopay.domain.exceptions import ForbiddenError, NotFoundError
from motopay.infrastructure.db.models import Cliente, Cobranca, Contrato, Operacao
from motopay.infrastructure.payments.mercadopago_client import (
    mp_credentials_complete,
    mp_public_key_for_operacao,
)
from motopay.interfaces.api.deps import CurrentUser
from motopay.interfaces.api.schemas import (
    CardPaymentOut,
    ClienteMpCardOut,
    CobrancaOut,
    PayerPortalOut,
)
from motopay.services.billing_service import (
    _OPEN_COBRANCA_STATUSES,
    _cobranca_to_out,
    _effective_operacao,
    ensure_pix_for_cobranca,
)
from motopay.services.card_payment_service import list_cliente_mp_cards, pay_cobranca_with_card


def _portal_base_url() -> str:
    s = get_settings()
    base = s.payer_portal_base_url.strip()
    if base:
        return base.rstrip("/")
    cors = [x.strip() for x in s.cors_origins.split(",") if x.strip() and x.strip() != "*"]
    if cors:
        return cors[0].rstrip("/")
    return "http://localhost:5173"


def portal_url_for_token(token: str) -> str:
    return f"{_portal_base_url()}/pay/{token}"


def _portal_ttl() -> timedelta:
    days = max(1, get_settings().payer_portal_token_ttl_days)
    return timedelta(days=days)


def _ensure_portal_token(cob: Cobranca, *, regenerate: bool = False) -> str:
    if cob.payment_portal_token and not regenerate:
        if cob.payment_portal_expires_at is None:
            cob.payment_portal_expires_at = datetime.now(UTC) + _portal_ttl()
        return cob.payment_portal_token
    token = secrets.token_urlsafe(32)
    cob.payment_portal_token = token
    cob.payment_portal_expires_at = datetime.now(UTC) + _portal_ttl()
    return token


def _portal_expired(cob: Cobranca) -> bool:
    expires = cob.payment_portal_expires_at
    if expires is None:
        return False
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    return expires < datetime.now(UTC)


def issue_portal_link(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    cobranca_id: int,
) -> dict[str, str]:
    operacao_id = _effective_operacao(user, operacao_scope)
    cob = db.get(Cobranca, cobranca_id)
    if not cob or cob.operacao_id != operacao_id:
        raise NotFoundError("Cobrança não encontrada")
    if cob.status not in _OPEN_COBRANCA_STATUSES:
        raise ForbiddenError("Cobrança não está aberta para pagamento")
    token = _ensure_portal_token(cob, regenerate=True)
    db.add(cob)
    db.commit()
    return {"token": token, "url": portal_url_for_token(token)}


def revoke_portal_link(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    cobranca_id: int,
) -> None:
    operacao_id = _effective_operacao(user, operacao_scope)
    cob = db.get(Cobranca, cobranca_id)
    if not cob or cob.operacao_id != operacao_id:
        raise NotFoundError("Cobrança não encontrada")
    cob.payment_portal_token = None
    cob.payment_portal_expires_at = None
    db.add(cob)
    db.commit()


def ensure_portal_url_for_cobranca(db: Session, cob: Cobranca) -> str | None:
    if cob.status not in _OPEN_COBRANCA_STATUSES:
        return None
    if _portal_expired(cob):
        cob.payment_portal_token = None
        cob.payment_portal_expires_at = None
    token = _ensure_portal_token(cob)
    db.add(cob)
    db.flush()
    return portal_url_for_token(token)


def _cob_by_portal_token(db: Session, token: str) -> Cobranca:
    cob = db.scalars(
        select(Cobranca).where(Cobranca.payment_portal_token == token)
    ).first()
    if not cob:
        raise NotFoundError("Link de pagamento inválido ou expirado")
    if _portal_expired(cob):
        raise ForbiddenError("Link de pagamento expirado")
    return cob


def get_portal_checkout(db: Session, token: str) -> PayerPortalOut:
    cob = _cob_by_portal_token(db, token)
    payable = cob.status in _OPEN_COBRANCA_STATUSES
    if not payable and cob.status != CobrancaStatus.RECEBIDO.value:
        raise ForbiddenError("Esta cobrança não está disponível para pagamento")
    ct = db.get(Contrato, cob.contrato_id)
    cliente = db.get(Cliente, ct.cliente_id) if ct else None
    op = db.get(Operacao, cob.operacao_id)
    if not ct or not cliente or not op:
        raise NotFoundError("Dados do pagamento não encontrados")
    if not mp_credentials_complete(op):
        raise ForbiddenError("Pagamento online indisponível para esta operação")
    today = date.today()
    out = _cobranca_to_out(cob, op, today, valor_base=ct.valor_recorrente)
    return PayerPortalOut(
        cobranca=out,
        cliente_nome=cliente.nome,
        cliente_id=cliente.id,
        cliente_email=cliente.email,
        cliente_cpf=cliente.cpf,
        mercadopago_public_key=mp_public_key_for_operacao(op),
        credentials_mode=effective_mercadopago_credentials_mode(),
        payable=payable,
    )


def list_portal_saved_cards(db: Session, token: str) -> list[ClienteMpCardOut]:
    cob = _cob_by_portal_token(db, token)
    ct = db.get(Contrato, cob.contrato_id)
    if not ct:
        raise NotFoundError("Dados do pagamento não encontrados")
    return list_cliente_mp_cards(db, ct.cliente_id, cob.operacao_id)


def portal_generate_pix(db: Session, token: str) -> CobrancaOut:
    cob = _cob_by_portal_token(db, token)

    class _PortalUser:
        role = None
        operacao_id = cob.operacao_id

    return ensure_pix_for_cobranca(
        db,
        _PortalUser(),  # type: ignore[arg-type]
        cob.operacao_id,
        cob.id,
    )


def portal_pay_card(
    db: Session,
    token: str,
    *,
    card_token: str,
    payment_method_id: str,
    payment_method_kind: str,
    installments: int,
    saved_card_id: int | None,
    device_id: str | None = None,
) -> CardPaymentOut:
    cob = _cob_by_portal_token(db, token)

    class _PortalUser:
        role = None
        operacao_id = cob.operacao_id

    kind = payment_method_kind if payment_method_kind in ("credit_card", "debit_card") else "credit_card"
    return pay_cobranca_with_card(
        db,
        _PortalUser(),  # type: ignore[arg-type]
        cob.operacao_id,
        cobranca_id=cob.id,
        token=card_token,
        payment_method_id=payment_method_id,
        payment_method_kind=kind,  # type: ignore[arg-type]
        saved_card_id=saved_card_id,
        installments=installments,
        device_id=device_id,
    )
