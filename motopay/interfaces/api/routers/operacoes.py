from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from motopay.domain.exceptions import ForbiddenError, NotFoundError
from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, require_admin, require_settings_access
from motopay.interfaces.api.schemas import (
    OperacaoCreate,
    OperacaoOut,
    OperacaoUpdate,
    TelegramTemplateMetaOut,
    TelegramTemplatePreviewOut,
    TelegramTemplatePreviewRequest,
)
from motopay.services.operacao_service import (
    create_operacao,
    get_operacao_or_404,
    get_telegram_template_meta,
    list_operacoes,
    operacao_to_out,
    preview_telegram_template,
    update_operacao,
)

router = APIRouter(prefix="/operacoes", tags=["operacoes"])


@router.get("/telegram-template-meta", response_model=list[TelegramTemplateMetaOut])
def telegram_template_meta(
    _: CurrentUser = Depends(require_settings_access),
) -> list[TelegramTemplateMetaOut]:
    return get_telegram_template_meta()


@router.post("/telegram-template-preview", response_model=TelegramTemplatePreviewOut)
def telegram_template_preview(
    body: TelegramTemplatePreviewRequest,
    _: CurrentUser = Depends(require_settings_access),
) -> TelegramTemplatePreviewOut:
    text = preview_telegram_template(key=body.key, template=body.template, context=body.context)
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
    return update_operacao(db, user.operacao_id, body)


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
