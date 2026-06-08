from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from motopay.config import get_settings
from motopay.domain.exceptions import ForbiddenError, MotoPayError, NotFoundError
from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, require_admin, require_settings_access, resolve_operacao_id
from motopay.interfaces.api.schemas import (
    CustomMessageTriggerMetaOut,
    MpOAuthStartOut,
    OperacaoCreate,
    OperacaoOut,
    OperacaoUpdate,
    TelegramTemplateMetaOut,
    TelegramTemplatePreviewOut,
    TelegramTemplatePreviewRequest,
)
from motopay.services.mercadopago_oauth_service import (
    complete_mercadopago_oauth,
    disconnect_mercadopago_oauth_for_operacao,
    start_mercadopago_oauth,
)
from motopay.services.operacao_service import (
    create_operacao,
    get_custom_message_triggers,
    get_operacao_or_404,
    get_telegram_template_meta,
    list_operacoes,
    operacao_to_out,
    preview_telegram_template,
    update_operacao,
)

router = APIRouter(prefix="/operacoes", tags=["operacoes"])


def _frontend_settings_url(query: str) -> str:
    s = get_settings()
    base = s.payer_portal_base_url.strip()
    if not base:
        cors = [x.strip() for x in s.cors_origins.split(",") if x.strip() and x.strip() != "*"]
        base = cors[0] if cors else "http://localhost:5173"
    return f"{base.rstrip('/')}/ajustes?{query}"


@router.get("/mp-oauth/start", response_model=MpOAuthStartOut)
def mercadopago_oauth_start(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_settings_access),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> MpOAuthStartOut:
    data = start_mercadopago_oauth(db, user, operacao_id)
    return MpOAuthStartOut.model_validate(data)


@router.get("/mp-oauth/callback")
def mercadopago_oauth_callback(
    db: Session = Depends(get_db),
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    if error or not code or not state:
        return RedirectResponse(url=_frontend_settings_url("mp_oauth=error"), status_code=302)
    try:
        complete_mercadopago_oauth(db, code=code, state=state)
    except (ForbiddenError, NotFoundError, MotoPayError) as exc:
        from urllib.parse import quote

        msg = quote(str(exc)[:200])
        return RedirectResponse(url=_frontend_settings_url(f"mp_oauth=error&detail={msg}"), status_code=302)
    return RedirectResponse(url=_frontend_settings_url("mp_oauth=ok"), status_code=302)


@router.post("/mp-oauth/disconnect")
def mercadopago_oauth_disconnect(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_settings_access),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> dict[str, bool]:
    disconnect_mercadopago_oauth_for_operacao(db, user, operacao_id)
    return {"ok": True}


@router.get("/telegram-template-meta", response_model=list[TelegramTemplateMetaOut])
def telegram_template_meta(
    _: CurrentUser = Depends(require_settings_access),
) -> list[TelegramTemplateMetaOut]:
    return get_telegram_template_meta()


@router.get("/custom-message-triggers", response_model=list[CustomMessageTriggerMetaOut])
def custom_message_triggers(
    _: CurrentUser = Depends(require_settings_access),
) -> list[CustomMessageTriggerMetaOut]:
    return get_custom_message_triggers()


@router.post("/telegram-template-preview", response_model=TelegramTemplatePreviewOut)
def telegram_template_preview(
    body: TelegramTemplatePreviewRequest,
    _: CurrentUser = Depends(require_settings_access),
) -> TelegramTemplatePreviewOut:
    text = preview_telegram_template(
        key=body.key,
        trigger=body.trigger,
        template=body.template,
        context=body.context,
    )
    return TelegramTemplatePreviewOut(text=text)


@router.get("", response_model=list[OperacaoOut])
def list_ops(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_admin),
) -> list[OperacaoOut]:
    return list_operacoes(db, user)


@router.post("", response_model=OperacaoOut)
def create_op(
    body: OperacaoCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> OperacaoOut:
    return create_operacao(db, body)


@router.get("/me", response_model=OperacaoOut)
def get_my_op(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_settings_access),
) -> OperacaoOut:
    if not user.operacao_id:
        raise ForbiddenError("Usuário sem operação vinculada")
    op = get_operacao_or_404(db, user.operacao_id)
    if not op:
        raise NotFoundError("Operação não encontrada")
    return operacao_to_out(op)


@router.patch("/me", response_model=OperacaoOut)
def update_my_op(
    body: OperacaoUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_settings_access),
) -> OperacaoOut:
    if not user.operacao_id:
        raise ForbiddenError("Usuário sem operação vinculada")
    return update_operacao(db, user.operacao_id, body, role=user.role)


@router.get("/{operacao_id:int}", response_model=OperacaoOut)
def get_op_by_id_admin(
    operacao_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> OperacaoOut:
    op = get_operacao_or_404(db, operacao_id)
    if not op:
        raise NotFoundError("Operação não encontrada")
    return operacao_to_out(op)


@router.patch("/{operacao_id:int}", response_model=OperacaoOut)
def update_op_by_id_admin(
    operacao_id: int,
    body: OperacaoUpdate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> OperacaoOut:
    if not get_operacao_or_404(db, operacao_id):
        raise NotFoundError("Operação não encontrada")
    return update_operacao(db, operacao_id, body)
