from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from motopay.domain.enums import (
    CicloCobranca,
    CobrancaStatus,
    ContratoStatus,
    DomainEventType,
    FinanceiroTipo,
    PaymentGateway,
    PaymentMethodType,
    UserRole,
)
from motopay.domain.exceptions import ForbiddenError, NotFoundError
from motopay.infrastructure.db.models import (
    Cliente,
    Cobranca,
    Contrato,
    EventoDominio,
    Financeiro,
    Operacao,
)
from motopay.infrastructure.payments.mercadopago_client import (
    MercadoPagoClient,
    mp_configured_for_operacao,
    mp_credentials_complete,
    payer_email_for_mercadopago,
)
from motopay.infrastructure.payments.order_utils import is_order_paid, order_total_amount
from motopay.interfaces.api.deps import CurrentUser
from motopay.interfaces.api.schemas import CobrancaOut
from motopay.services.late_fee import LateAmounts, calculate_late_amounts
from motopay.services.mercadopago_token_service import ensure_valid_mp_token
from motopay.services.payment_gateway import (
    cancel_external_payment,
    create_pix_for_cobranca,
    create_pix_for_contrato,
)
from motopay.services.scoring_service import recalculate_cliente_score

logger = logging.getLogger(__name__)


def _today() -> date:
    """Data atual no fuso horário configurado (America/Sao_Paulo por padrão)."""
    from motopay.config import get_settings
    tz = ZoneInfo(get_settings().app_timezone)
    return datetime.now(tz).date()


_CHARGEBACK_LOST_STATUSES = frozenset({"lost", "charged_back", "settled", "closed"})

_OPEN_COBRANCA_STATUSES = (
    CobrancaStatus.PENDENTE.value,
    CobrancaStatus.ATRASADO.value,
)


def add_cycle(d: date, ciclo: str) -> date:
    if ciclo == CicloCobranca.SEMANAL.value:
        return d + timedelta(days=7)
    return d + relativedelta(months=1)


def _effective_operacao(user: CurrentUser, operacao_scope: int | None) -> int:
    if user.role == UserRole.DONO:
        if user.operacao_id is None:
            raise ForbiddenError("Operação não definida")
        return user.operacao_id
    if operacao_scope is None:
        raise ForbiddenError("Informe operacao_id")
    return operacao_scope


def _cobranca_query(user: CurrentUser, operacao_scope: int | None):
    q = select(Cobranca)
    if user.role == UserRole.DONO:
        q = q.where(Cobranca.operacao_id == user.operacao_id)
    elif operacao_scope is not None:
        q = q.where(Cobranca.operacao_id == operacao_scope)
    return q


def charge_amounts_for_cobranca(
    cob: Cobranca,
    ct: Contrato,
    op: Operacao,
    today: date,
) -> LateAmounts:
    return calculate_late_amounts(
        valor_base=ct.valor_recorrente,
        vencimento=cob.vencimento,
        operacao=op,
        today=today,
    )


def charge_amounts_for_contrato(
    ct: Contrato,
    op: Operacao,
    today: date,
) -> LateAmounts:
    return calculate_late_amounts(
        valor_base=ct.valor_recorrente,
        vencimento=ct.proximo_vencimento,
        operacao=op,
        today=today,
    )


def get_open_cobranca(db: Session, contrato_id: int) -> Cobranca | None:
    return db.scalars(
        select(Cobranca)
        .where(
            Cobranca.contrato_id == contrato_id,
            Cobranca.status.in_(_OPEN_COBRANCA_STATUSES),
        )
        .order_by(Cobranca.id.desc())
    ).first()


def _cobranca_to_out(
    c: Cobranca,
    op: Operacao | None,
    today: date,
    *,
    valor_base: Decimal | None = None,
) -> CobrancaOut:
    base = valor_base if valor_base is not None else c.valor
    display_status = c.status
    pendente_ou_atrasado = c.status in _OPEN_COBRANCA_STATUSES
    if pendente_ou_atrasado and c.vencimento < today:
        amounts = calculate_late_amounts(
            valor_base=base,
            vencimento=c.vencimento,
            operacao=op,
            today=today,
        )
        display_status = CobrancaStatus.ATRASADO.value
    else:
        amounts = calculate_late_amounts(
            valor_base=base,
            vencimento=c.vencimento,
            operacao=op,
            today=today,
        )

    return CobrancaOut(
        id=c.id,
        operacao_id=c.operacao_id,
        contrato_id=c.contrato_id,
        valor=base,
        vencimento=c.vencimento,
        mercadopago_payment_id=c.mercadopago_payment_id,
        mercadopago_order_id=c.mercadopago_order_id,
        payment_gateway=c.payment_gateway or PaymentGateway.MERCADOPAGO.value,
        payment_method_type=c.payment_method_type,
        pix_copia_cola=c.pix_copia_cola,
        status=display_status,
        dias_atraso=amounts.dias_atraso,
        multa=amounts.multa,
        juros=amounts.juros,
        valor_total=amounts.valor_total,
        valor_estornado=c.valor_estornado,
        mercadopago_dispute_status=c.mercadopago_dispute_status,
        mercadopago_payment_status=c.mercadopago_payment_status,
    )


def late_amounts_for_contrato(
    db: Session,
    contrato: Contrato,
    today: date,
) -> LateAmounts:
    op = db.get(Operacao, contrato.operacao_id)
    return calculate_late_amounts(
        valor_base=contrato.valor_recorrente,
        vencimento=contrato.proximo_vencimento,
        operacao=op,
        today=today,
    )


def _apply_pix_to_cobranca(
    cob: Cobranca,
    *,
    order_id: str,
    payment_id: str,
    pix: str | None,
    gateway: str,
    valor: Decimal,
    status: str,
) -> None:
    cob.valor = valor
    cob.pix_copia_cola = pix
    cob.payment_gateway = gateway
    cob.status = status
    cob.mercadopago_order_id = order_id
    cob.mercadopago_payment_id = payment_id
    cob.payment_method_type = PaymentMethodType.PIX.value


def refresh_overdue_pix(db: Session, *, contrato: Contrato, today: date) -> Cobranca | None:
    if contrato.status != ContratoStatus.ATIVO.value:
        return None
    if contrato.proximo_vencimento >= today:
        return None

    op = db.get(Operacao, contrato.operacao_id)
    if not op:
        return None

    amounts = calculate_late_amounts(
        valor_base=contrato.valor_recorrente,
        vencimento=contrato.proximo_vencimento,
        operacao=op,
        today=today,
    )
    if amounts.dias_atraso <= 0:
        return None

    cliente = db.get(Cliente, contrato.cliente_id)
    if not cliente:
        return None

    cob = get_open_cobranca(db, contrato.id)
    if (
        cob is not None
        and cob.status == CobrancaStatus.ATRASADO.value
        and cob.valor == amounts.valor_total
        and cob.mercadopago_payment_id
        and cob.pix_copia_cola
    ):
        return cob

    # Cria o novo PIX ANTES de cancelar o antigo — garante que sempre existe um
    # código válido mesmo que o cancelamento falhe.
    order_id, payment_id, pix, gw = create_pix_for_contrato(
        op=op,
        cliente=cliente,
        contrato_id=contrato.id,
        valor_total=amounts.valor_total,
        due_date=today,
        db=db,
    )

    if cob is not None:
        cancel_external_payment(
            gateway=cob.payment_gateway,
            payment_id=cob.mercadopago_payment_id,
            order_id=cob.mercadopago_order_id,
            op=op,
            db=db,
        )

    if cob is None:
        cob = Cobranca(
            operacao_id=contrato.operacao_id,
            contrato_id=contrato.id,
            valor=amounts.valor_total,
            vencimento=contrato.proximo_vencimento,
            status=CobrancaStatus.ATRASADO.value,
        )
        db.add(cob)
    _apply_pix_to_cobranca(
        cob,
        order_id=order_id,
        payment_id=payment_id,
        pix=pix,
        gateway=gw,
        valor=amounts.valor_total,
        status=CobrancaStatus.ATRASADO.value,
    )
    db.add(cob)
    db.flush()
    return cob


def ensure_pix_for_cobranca(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    cobranca_id: int,
) -> CobrancaOut:
    operacao_id = _effective_operacao(user, operacao_scope)
    cob = db.get(Cobranca, cobranca_id)
    if not cob or cob.operacao_id != operacao_id:
        raise NotFoundError("Cobrança não encontrada")
    if cob.status not in _OPEN_COBRANCA_STATUSES:
        raise ForbiddenError("Cobrança não está aberta")
    today = _today()
    ct = db.get(Contrato, cob.contrato_id)
    op = db.get(Operacao, operacao_id)
    if not ct or not op:
        raise NotFoundError("Dados do contrato não encontrados")
    amounts = charge_amounts_for_cobranca(cob, ct, op, today)
    if (
        cob.pix_copia_cola
        and cob.mercadopago_order_id
        and cob.valor == amounts.valor_total
    ):
        return _cobranca_to_out(cob, op, today, valor_base=ct.valor_recorrente)

    cliente = db.get(Cliente, ct.cliente_id)
    if not cliente:
        raise NotFoundError("Dados do contrato não encontrados")
    if not mp_credentials_complete(op) and mp_configured_for_operacao(op):
        raise ForbiddenError(
            "Credenciais Mercado Pago incompletas. Configure Access Token, Public Key e "
            "Webhook Secret em Ajustes."
        )

    display_status = (
        CobrancaStatus.ATRASADO.value
        if amounts.dias_atraso > 0
        else cob.status
    )
    # Cria o novo PIX PRIMEIRO — garante que o cliente sempre tem um código válido.
    # Só cancela o antigo após commit do novo (mesmo padrão de refresh_overdue_pix).
    old_gateway = cob.payment_gateway
    old_payment_id = cob.mercadopago_payment_id
    old_order_id = cob.mercadopago_order_id
    order_id, payment_id, pix, gw = create_pix_for_cobranca(
        op=op,
        cliente=cliente,
        cobranca_id=cob.id,
        valor_total=amounts.valor_total,
        due_date=cob.vencimento,
        db=db,
    )
    _apply_pix_to_cobranca(
        cob,
        order_id=order_id,
        payment_id=payment_id,
        pix=pix,
        gateway=gw,
        valor=amounts.valor_total,
        status=display_status,
    )
    db.add(cob)
    db.commit()
    db.refresh(cob)
    if old_payment_id or old_order_id:
        cancel_external_payment(
            gateway=old_gateway,
            payment_id=old_payment_id,
            order_id=old_order_id,
            op=op,
            db=db,
        )
    return _cobranca_to_out(cob, op, today, valor_base=ct.valor_recorrente)


def create_pix_charge_for_contract(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    contrato_id: int,
) -> CobrancaOut:
    operacao_id = _effective_operacao(user, operacao_scope)
    ct = db.get(Contrato, contrato_id)
    if not ct or ct.operacao_id != operacao_id:
        raise NotFoundError("Contrato não encontrado")
    cliente = db.get(Cliente, ct.cliente_id)
    if not cliente:
        raise NotFoundError("Cliente não encontrado")
    op = db.get(Operacao, operacao_id)
    if not op:
        raise NotFoundError("Operação não encontrada")
    today = _today()
    amounts = charge_amounts_for_contrato(ct, op, today)

    # Reutiliza cobrança aberta se já existe com Pix e valor igual
    existing = get_open_cobranca(db, ct.id)
    if (
        existing is not None
        and existing.pix_copia_cola
        and existing.mercadopago_order_id
        and existing.valor == amounts.valor_total
    ):
        return _cobranca_to_out(existing, op, today, valor_base=ct.valor_recorrente)

    # Cria o novo PIX primeiro para garantir continuidade de pagamento
    order_id, payment_id, pix, gw = create_pix_for_contrato(
        op=op,
        cliente=cliente,
        contrato_id=ct.id,
        valor_total=amounts.valor_total,
        due_date=ct.proximo_vencimento,
        db=db,
    )

    if existing is not None:
        # Atualiza a cobrança existente e cancela o PIX antigo — evita duplicidade
        old_order_id = existing.mercadopago_order_id
        _apply_pix_to_cobranca(
            existing,
            order_id=order_id,
            payment_id=payment_id,
            pix=pix,
            gateway=gw,
            valor=amounts.valor_total,
            status=(
                CobrancaStatus.ATRASADO.value
                if amounts.dias_atraso > 0
                else CobrancaStatus.PENDENTE.value
            ),
        )
        db.add(existing)
        db.commit()
        db.refresh(existing)
        cancel_external_payment(
            gateway=existing.payment_gateway,
            payment_id=None,
            order_id=old_order_id,
            op=op,
            db=db,
        )
        return _cobranca_to_out(existing, op, today, valor_base=ct.valor_recorrente)

    new_status = (
        CobrancaStatus.ATRASADO.value
        if amounts.dias_atraso > 0
        else CobrancaStatus.PENDENTE.value
    )
    cob = Cobranca(
        operacao_id=operacao_id,
        contrato_id=ct.id,
        valor=amounts.valor_total,
        vencimento=ct.proximo_vencimento,
        pix_copia_cola=pix,
        payment_gateway=gw,
        status=new_status,
    )
    _apply_pix_to_cobranca(
        cob,
        order_id=order_id,
        payment_id=payment_id,
        pix=pix,
        gateway=gw,
        valor=amounts.valor_total,
        status=new_status,
    )
    db.add(cob)
    db.commit()
    db.refresh(cob)
    return _cobranca_to_out(cob, op, today, valor_base=ct.valor_recorrente)


def create_mercadopago_subscription_for_contract(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    contrato_id: int,
) -> dict[str, str | int | None]:
    operacao_id = _effective_operacao(user, operacao_scope)
    ct = db.get(Contrato, contrato_id)
    if not ct or ct.operacao_id != operacao_id:
        raise NotFoundError("Contrato não encontrado")
    op = db.get(Operacao, operacao_id)
    if not op:
        raise NotFoundError("Operação não encontrada")
    if not mp_credentials_complete(op):
        raise ForbiddenError("Mercado Pago não configurado ou credenciais incompletas")
    cliente = db.get(Cliente, ct.cliente_id)
    if not cliente:
        raise NotFoundError("Cliente não encontrado")
    client = MercadoPagoClient(access_token=ensure_valid_mp_token(db, op))
    data = client.create_preapproval(
        external_reference=f"contrato-{ct.id}",
        value=ct.valor_recorrente,
        reason=f"Contrato #{ct.id}",
        payer_email=payer_email_for_mercadopago(cliente),
        ciclo=ct.ciclo,
    )
    sub_id = str(data["id"])
    ct.mercadopago_subscription_id = sub_id
    ct.mercadopago_subscription_status = str(data.get("status", "pending"))
    db.add(ct)
    db.commit()
    return {
        "contrato_id": ct.id,
        "mercadopago_subscription_id": sub_id,
        "init_point": MercadoPagoClient.preapproval_init_point(data),
        "status": str(data.get("status", "pending")),
    }


def get_mercadopago_subscription_link(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    contrato_id: int,
) -> dict[str, str | int | None]:
    operacao_id = _effective_operacao(user, operacao_scope)
    ct = db.get(Contrato, contrato_id)
    if not ct or ct.operacao_id != operacao_id:
        raise NotFoundError("Contrato não encontrado")
    if not ct.mercadopago_subscription_id:
        raise NotFoundError("Contrato sem assinatura Mercado Pago")
    op = db.get(Operacao, operacao_id)
    if not op or not mp_credentials_complete(op):
        raise ForbiddenError("Mercado Pago não configurado")
    data = MercadoPagoClient(access_token=ensure_valid_mp_token(db, op)).get_preapproval(
        ct.mercadopago_subscription_id
    )
    status = str(data.get("status", ""))
    if status:
        ct.mercadopago_subscription_status = status
        db.add(ct)
        db.commit()
    return {
        "contrato_id": ct.id,
        "mercadopago_subscription_id": ct.mercadopago_subscription_id,
        "init_point": MercadoPagoClient.preapproval_init_point(data),
        "status": status,
    }


def cancel_mercadopago_subscription_for_contract(
    db: Session,
    contrato: Contrato,
) -> None:
    if not contrato.mercadopago_subscription_id:
        return
    op = db.get(Operacao, contrato.operacao_id)
    if not op or not mp_configured_for_operacao(op):
        return
    try:
        MercadoPagoClient(access_token=ensure_valid_mp_token(db, op)).cancel_preapproval(
            contrato.mercadopago_subscription_id
        )
        contrato.mercadopago_subscription_status = "cancelled"
        db.add(contrato)
    except Exception as exc:
        # Não atualiza o status em banco — permite nova tentativa futura.
        logger.exception(
            "Falha ao cancelar assinatura MP contrato=%s sub=%s — status mantido para nova tentativa",
            contrato.id,
            contrato.mercadopago_subscription_id,
        )
        from motopay.infrastructure.telegram.owner_notify import (
            notify_owner_subscription_cancel_failure,
        )
        notify_owner_subscription_cancel_failure(
            operacao=op,
            contrato_id=contrato.id,
            subscription_id=contrato.mercadopago_subscription_id or "",
            error=str(exc),
        )


def sync_mercadopago_subscription_amount(
    db: Session,
    contrato: Contrato,
    *,
    amount: Decimal | None = None,
) -> None:
    if not contrato.mercadopago_subscription_id:
        return
    op = db.get(Operacao, contrato.operacao_id)
    if not op or not mp_configured_for_operacao(op):
        return
    value = amount if amount is not None else contrato.valor_recorrente
    try:
        MercadoPagoClient(access_token=ensure_valid_mp_token(db, op)).update_preapproval_amount(
            contrato.mercadopago_subscription_id,
            value=value,
            ciclo=contrato.ciclo,
        )
    except Exception:
        logger.exception(
            "Falha ao atualizar valor da assinatura MP contrato=%s", contrato.id
        )


def refund_cobranca_mercadopago(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    cobranca_id: int,
    *,
    amount: Decimal | None = None,
) -> CobrancaOut:
    from motopay.infrastructure.payments.mercadopago_client import (
        MercadoPagoApiError,
        mercadopago_api_error_message,
    )

    operacao_id = _effective_operacao(user, operacao_scope)
    cob = db.get(Cobranca, cobranca_id)
    if not cob or cob.operacao_id != operacao_id:
        raise NotFoundError("Cobrança não encontrada")
    if cob.status != CobrancaStatus.RECEBIDO.value:
        raise ForbiddenError("Só é possível estornar cobranças recebidas")
    payment_id = cob.mercadopago_payment_id
    if not payment_id:
        raise ForbiddenError("Cobrança sem pagamento Mercado Pago para estorno")
    op = db.get(Operacao, operacao_id)
    if not op or not mp_credentials_complete(op):
        raise ForbiddenError("Mercado Pago não configurado")
    already = cob.valor_estornado or Decimal(0)
    remaining = cob.valor - already
    if remaining <= 0:
        raise ForbiddenError("Cobrança já totalmente estornada")
    refund_amount = amount if amount is not None else remaining
    if refund_amount > remaining:
        raise ForbiddenError(f"Valor máximo estornável: {remaining}")
    client = MercadoPagoClient(access_token=ensure_valid_mp_token(db, op))
    try:
        refund_data = client.create_refund(payment_id, amount=refund_amount)
    except MercadoPagoApiError as exc:
        raise ForbiddenError(
            f"Falha ao estornar no Mercado Pago: {mercadopago_api_error_message(exc)}"
        ) from exc
    _, ev_id = handle_mercadopago_refund_confirmed(
        db,
        mercadopago_payment_id=payment_id,
        refund_amount=refund_amount,
        refund_data=refund_data,
    )
    if ev_id:
        from motopay.infrastructure.messaging.tasks import handle_domain_event

        handle_domain_event.delay(ev_id)
    db.refresh(cob)
    ct = db.get(Contrato, cob.contrato_id)
    valor_base = ct.valor_recorrente if ct else cob.valor
    return _cobranca_to_out(cob, op, _today(), valor_base=valor_base)


def get_cobranca(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    cobranca_id: int,
) -> CobrancaOut:
    operacao_id = _effective_operacao(user, operacao_scope)
    cob = db.get(Cobranca, cobranca_id)
    if not cob:
        raise NotFoundError("Cobrança não encontrada")
    if user.role == UserRole.DONO and cob.operacao_id != user.operacao_id:
        raise ForbiddenError("Cobrança fora do escopo")
    if user.role == UserRole.ADMIN and operacao_scope is not None and cob.operacao_id != operacao_scope:
        raise ForbiddenError("Cobrança fora do escopo")
    op = db.get(Operacao, cob.operacao_id)
    ct = db.get(Contrato, cob.contrato_id)
    valor_base = ct.valor_recorrente if ct else cob.valor
    return _cobranca_to_out(cob, op, _today(), valor_base=valor_base)


def list_cobrancas(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    *,
    limit: int,
    offset: int,
    status: CobrancaStatus | None = None,
) -> tuple[list[CobrancaOut], int]:
    base = _cobranca_query(user, operacao_scope)
    if status is not None:
        base = base.where(Cobranca.status == status.value)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = list(db.scalars(base.order_by(Cobranca.id.desc()).limit(limit).offset(offset)).all())
    today = _today()
    op_ids = {c.operacao_id for c in rows}
    ops: dict[int, Operacao] = {}
    if op_ids:
        for o in db.scalars(select(Operacao).where(Operacao.id.in_(op_ids))).all():
            ops[o.id] = o
    ct_ids = {c.contrato_id for c in rows}
    contratos: dict[int, Contrato] = {}
    if ct_ids:
        for ct in db.scalars(select(Contrato).where(Contrato.id.in_(ct_ids))).all():
            contratos[ct.id] = ct
    out: list[CobrancaOut] = []
    for c in rows:
        ct = contratos.get(c.contrato_id)
        valor_base = ct.valor_recorrente if ct else c.valor
        out.append(_cobranca_to_out(c, ops.get(c.operacao_id), today, valor_base=valor_base))
    return out, int(total)


def list_cobrancas_for_cliente(
    db: Session,
    *,
    cliente_id: int,
    limit: int,
    offset: int,
) -> tuple[list[CobrancaOut], int]:
    q = (
        select(Cobranca)
        .join(Contrato, Contrato.id == Cobranca.contrato_id)
        .where(Contrato.cliente_id == cliente_id)
    )
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(db.scalars(q.order_by(Cobranca.id.desc()).limit(limit).offset(offset)).all())
    today = _today()
    out: list[CobrancaOut] = []
    for c in rows:
        ct = db.get(Contrato, c.contrato_id)
        op = db.get(Operacao, c.operacao_id)
        valor_base = ct.valor_recorrente if ct else c.valor
        out.append(_cobranca_to_out(c, op, today, valor_base=valor_base))
    return out, int(total)


def get_active_contrato_for_cliente(db: Session, cliente_id: int) -> Contrato | None:
    return db.scalars(
        select(Contrato)
        .where(
            Contrato.cliente_id == cliente_id,
            Contrato.status == ContratoStatus.ATIVO.value,
        )
        .order_by(Contrato.id.desc())
    ).first()


def _emit_domain_event(db: Session, tipo: str, payload: dict) -> int:
    ev = EventoDominio(tipo=tipo, payload=payload)
    db.add(ev)
    db.flush()
    return ev.id


def _financeiro_with_desc_exists(db: Session, operacao_id: int, descricao: str) -> bool:
    existing = db.scalars(
        select(Financeiro).where(
            Financeiro.operacao_id == operacao_id,
            Financeiro.descricao == descricao,
        )
    ).first()
    return existing is not None


def _finalize_payment(
    db: Session,
    cob: Cobranca,
    *,
    external_id: str,
    gateway: str,
    value: Decimal | None,
) -> tuple[bool, int | None]:
    if cob.status == CobrancaStatus.RECEBIDO.value:
        return True, None

    cob.status = CobrancaStatus.RECEBIDO.value
    db.add(cob)

    ct = db.get(Contrato, cob.contrato_id)
    if not ct:
        db.commit()
        return True, None

    was_inadimplente = bool(ct.inadimplente or ct.dias_atraso_acumulado > 0)
    amount = value if value is not None else cob.valor
    fin = Financeiro(
        operacao_id=cob.operacao_id,
        tipo=FinanceiroTipo.RECEITA.value,
        valor=amount,
        descricao=f"Pagamento confirmado ({gateway} {external_id})",
        data=_today(),
        moto_id=ct.moto_id,
        contrato_id=ct.id,
    )
    db.add(fin)

    ct.proximo_vencimento = add_cycle(ct.proximo_vencimento, ct.ciclo)
    ct.inadimplente = False
    ct.nivel_escalonamento_cobranca = 0
    ct.dias_atraso_acumulado = 0
    ct.promessa_pagamento_em = None
    ct.promessa_notas = None
    db.add(ct)

    cliente = db.get(Cliente, ct.cliente_id)
    if cliente:
        recalculate_cliente_score(db, cliente, on_time_payment_delta=5)

    payload: dict = {
        "contrato_id": ct.id,
        "cliente_id": ct.cliente_id,
        "operacao_id": cob.operacao_id,
        "mercadopago_payment_id": external_id,
    }

    ev_id = _emit_domain_event(db, DomainEventType.PAGAMENTO_CONFIRMADO.value, payload)
    if was_inadimplente and ct.mercadopago_subscription_id:
        sync_mercadopago_subscription_amount(db, ct)
    db.commit()
    return True, ev_id


def handle_mercadopago_refund_confirmed(
    db: Session,
    *,
    mercadopago_payment_id: str,
    refund_amount: Decimal,
    refund_data: dict | None = None,
) -> tuple[bool, int | None]:
    del refund_data
    cob = db.scalars(
        select(Cobranca).where(Cobranca.mercadopago_payment_id == mercadopago_payment_id)
    ).first()
    if not cob:
        return False, None
    prev = cob.valor_estornado or Decimal(0)
    target = min(prev + refund_amount, cob.valor)
    delta = target - prev
    if delta <= 0:
        return True, None
    cob.valor_estornado = target
    if target >= cob.valor:
        cob.status = CobrancaStatus.CANCELADO.value
    db.add(cob)
    ct = db.get(Contrato, cob.contrato_id)
    fin = Financeiro(
        operacao_id=cob.operacao_id,
        tipo=FinanceiroTipo.DESPESA.value,
        valor=delta,
        descricao=f"Estorno Mercado Pago (payment {mercadopago_payment_id})",
        data=_today(),
        moto_id=ct.moto_id if ct else None,
        contrato_id=cob.contrato_id,
    )
    db.add(fin)
    ev_id = _emit_domain_event(
        db,
        DomainEventType.ESTORNO_CONFIRMADO.value,
        {
            "cobranca_id": cob.id,
            "contrato_id": cob.contrato_id,
            "operacao_id": cob.operacao_id,
            "cliente_id": ct.cliente_id if ct else None,
            "delta": str(delta),
            "valor_estornado": str(target),
            "mercadopago_payment_id": mercadopago_payment_id,
        },
    )
    db.commit()
    return True, ev_id


def sync_refund_from_mercadopago_payment(
    db: Session,
    *,
    pay_data: dict,
) -> tuple[bool, int | None]:
    payment_id = str(pay_data.get("id", "")).strip()
    if not payment_id:
        return False, None
    status = str(pay_data.get("status", "")).lower()
    raw_refunded = pay_data.get("transaction_amount_refunded")
    refunded = Decimal(str(raw_refunded)) if raw_refunded is not None else Decimal(0)
    if refunded <= 0 and status not in ("refunded", "partially_refunded"):
        return False, None
    cob = db.scalars(
        select(Cobranca).where(Cobranca.mercadopago_payment_id == payment_id)
    ).first()
    if not cob:
        return False, None
    prev = cob.valor_estornado or Decimal(0)
    target = refunded if refunded > 0 else cob.valor
    target = min(target, cob.valor)
    delta = target - prev
    if delta <= 0:
        return True, None
    cob.valor_estornado = target
    if target >= cob.valor or status == "refunded":
        cob.status = CobrancaStatus.CANCELADO.value
    db.add(cob)
    ct = db.get(Contrato, cob.contrato_id)
    fin = Financeiro(
        operacao_id=cob.operacao_id,
        tipo=FinanceiroTipo.DESPESA.value,
        valor=delta,
        descricao=f"Estorno confirmado via webhook (payment {payment_id})",
        data=_today(),
        moto_id=ct.moto_id if ct else None,
        contrato_id=cob.contrato_id,
    )
    db.add(fin)
    ev_id = _emit_domain_event(
        db,
        DomainEventType.ESTORNO_CONFIRMADO.value,
        {
            "cobranca_id": cob.id,
            "contrato_id": cob.contrato_id,
            "operacao_id": cob.operacao_id,
            "cliente_id": ct.cliente_id if ct else None,
            "delta": str(delta),
            "valor_estornado": str(target),
            "mercadopago_payment_id": payment_id,
        },
    )
    db.commit()
    return True, ev_id


def handle_mercadopago_chargeback(
    db: Session,
    *,
    chargeback_data: dict,
) -> tuple[bool, int | None]:
    payment_id = chargeback_data.get("payment_id")
    if payment_id is None:
        payments = chargeback_data.get("payments") or []
        if payments and isinstance(payments[0], dict):
            payment_id = payments[0].get("id")
    if payment_id is None:
        return False, None
    payment_id = str(payment_id)
    cob = db.scalars(
        select(Cobranca).where(Cobranca.mercadopago_payment_id == payment_id)
    ).first()
    if not cob:
        return False, None
    status = str(chargeback_data.get("status", "opened")).strip() or "opened"
    cob.mercadopago_dispute_status = status
    db.add(cob)
    ct = db.get(Contrato, cob.contrato_id)
    ev_id: int | None = None
    if status.lower() in _CHARGEBACK_LOST_STATUSES:
        raw_amount = chargeback_data.get("amount") or chargeback_data.get("transaction_amount")
        if raw_amount is not None:
            cb_amount = Decimal(str(raw_amount))
        else:
            cb_amount = cob.valor - (cob.valor_estornado or Decimal(0))
        desc = f"Chargeback {status} (payment {payment_id})"
        if cb_amount > 0 and not _financeiro_with_desc_exists(db, cob.operacao_id, desc):
            fin = Financeiro(
                operacao_id=cob.operacao_id,
                tipo=FinanceiroTipo.DESPESA.value,
                valor=cb_amount,
                descricao=desc,
                data=_today(),
                moto_id=ct.moto_id if ct else None,
                contrato_id=cob.contrato_id,
            )
            db.add(fin)
    ev_id = _emit_domain_event(
        db,
        DomainEventType.CHARGEBACK_ATUALIZADO.value,
        {
            "cobranca_id": cob.id,
            "contrato_id": cob.contrato_id,
            "operacao_id": cob.operacao_id,
            "cliente_id": ct.cliente_id if ct else None,
            "status": status,
            "mercadopago_payment_id": payment_id,
        },
    )
    db.commit()
    return True, ev_id


def handle_mercadopago_payment_confirmed(
    db: Session,
    *,
    mercadopago_payment_id: str,
    value: Decimal | None = None,
) -> tuple[bool, int | None]:
    # with_for_update evita duplo-avanço de proximo_vencimento quando o MP reentrega o webhook.
    cob = db.scalars(
        select(Cobranca)
        .where(Cobranca.mercadopago_payment_id == mercadopago_payment_id)
        .with_for_update()
    ).first()
    if not cob:
        return False, None
    return _finalize_payment(
        db,
        cob,
        external_id=mercadopago_payment_id,
        gateway=PaymentGateway.MERCADOPAGO.value,
        value=value,
    )


def handle_mercadopago_preapproval_updated(
    db: Session,
    *,
    preapproval_id: str,
    preapproval_data: dict,
) -> None:
    ext = str(preapproval_data.get("external_reference") or "")
    if not ext.startswith("contrato-"):
        ct = db.scalars(
            select(Contrato).where(Contrato.mercadopago_subscription_id == preapproval_id)
        ).first()
    else:
        try:
            ct_id = int(ext.split("-", 1)[1])
        except (IndexError, ValueError):
            return
        ct = db.get(Contrato, ct_id)
    if not ct:
        return
    ct.mercadopago_subscription_id = preapproval_id
    status = str(preapproval_data.get("status", "")).strip()
    if status:
        ct.mercadopago_subscription_status = status
    db.add(ct)
    db.commit()


def handle_mercadopago_subscription_payment(
    db: Session,
    *,
    mercadopago_payment_id: str,
    pay_data: dict,
    value: Decimal | None = None,
) -> tuple[bool, int | None]:
    existing = db.scalars(
        select(Cobranca).where(Cobranca.mercadopago_payment_id == mercadopago_payment_id)
    ).first()
    if existing:
        return handle_mercadopago_payment_confirmed(
            db, mercadopago_payment_id=mercadopago_payment_id, value=value
        )

    preapproval_id = pay_data.get("preapproval_id")
    if preapproval_id is not None:
        preapproval_id = str(preapproval_id)
    ext = str(pay_data.get("external_reference") or "")

    ct: Contrato | None = None
    if preapproval_id:
        ct = db.scalars(
            select(Contrato).where(Contrato.mercadopago_subscription_id == preapproval_id)
        ).first()
    if not ct and ext.startswith("contrato-"):
        try:
            ct_id = int(ext.split("-", 1)[1])
            ct = db.get(Contrato, ct_id)
        except (IndexError, ValueError):
            ct = None
    if not ct:
        return False, None

    op = db.get(Operacao, ct.operacao_id)
    today = _today()
    amounts = charge_amounts_for_contrato(ct, op, today) if op else None
    cob = get_open_cobranca(db, ct.id)
    if not cob:
        cob = Cobranca(
            operacao_id=ct.operacao_id,
            contrato_id=ct.id,
            valor=amounts.valor_total if amounts else ct.valor_recorrente,
            vencimento=ct.proximo_vencimento,
            status=(
                CobrancaStatus.ATRASADO.value
                if amounts and amounts.dias_atraso > 0
                else CobrancaStatus.PENDENTE.value
            ),
            payment_gateway=PaymentGateway.MERCADOPAGO.value,
        )
        db.add(cob)
        db.flush()
    elif amounts and amounts.dias_atraso > 0:
        cob.valor = amounts.valor_total
        cob.status = CobrancaStatus.ATRASADO.value
        db.add(cob)

    cob.mercadopago_payment_id = mercadopago_payment_id
    cob.payment_gateway = PaymentGateway.MERCADOPAGO.value
    raw_val = value if value is not None else pay_data.get("transaction_amount")
    amount = Decimal(str(raw_val)) if raw_val is not None else None
    return _finalize_payment(
        db,
        cob,
        external_id=mercadopago_payment_id,
        gateway=PaymentGateway.MERCADOPAGO.value,
        value=amount,
    )


def handle_mercadopago_order_confirmed(
    db: Session,
    *,
    mercadopago_order_id: str,
    order_data: dict | None = None,
    value: Decimal | None = None,
) -> tuple[bool, int | None]:
    cob = db.scalars(
        select(Cobranca)
        .where(Cobranca.mercadopago_order_id == mercadopago_order_id)
        .with_for_update()
    ).first()
    if not cob:
        return False, None
    if order_data and not is_order_paid(order_data):
        return False, None
    amount = value
    if amount is None and order_data:
        amount = order_total_amount(order_data)
    ext = cob.mercadopago_payment_id or mercadopago_order_id
    return _finalize_payment(
        db,
        cob,
        external_id=ext,
        gateway=PaymentGateway.MERCADOPAGO.value,
        value=amount,
    )
