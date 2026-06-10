from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from motopay.domain.enums import UserRole
from motopay.domain.exceptions import ConflictError, ForbiddenError, MotoPayError, NotFoundError
from motopay.infrastructure.db.models import Operacao, Usuario
from motopay.infrastructure.telegram.templates import (
    list_custom_message_triggers,
    list_template_meta,
    merge_template_overrides,
    render_custom_body,
    render_template,
    resolve_bot_menu_buttons,
    resolve_templates,
    sample_context_for_key,
    validate_bot_menu_buttons,
    validate_custom_messages,
)
from motopay.interfaces.api.deps import CurrentUser
from motopay.interfaces.api.schemas import (
    OperacaoCreate,
    OperacaoOut,
    OperacaoUpdate,
    TelegramBotMenuButton,
    TelegramCustomMessage,
    UserAdminOut,
    UsuarioCreate,
)
from motopay.services.auth_service import hash_password


def _custom_messages_out(op: Operacao) -> list[TelegramCustomMessage]:
    raw = op.telegram_custom_messages or []
    return [TelegramCustomMessage.model_validate(m) for m in raw]


def _bot_menu_buttons_out(op: Operacao) -> list[TelegramBotMenuButton]:
    raw = resolve_bot_menu_buttons(op.telegram_bot_menu_buttons)
    return [TelegramBotMenuButton.model_validate(b) for b in raw]


def operacao_to_out(op: Operacao) -> OperacaoOut:
    return OperacaoOut(
        id=op.id,
        nome=op.nome,
        created_at=op.created_at,
        multa_fixa_percentual=op.multa_fixa_percentual,
        juros_diario_percentual=op.juros_diario_percentual,
        telegram_templates=resolve_templates(op.telegram_templates),
        telegram_custom_messages=_custom_messages_out(op),
        telegram_bot_menu_buttons=_bot_menu_buttons_out(op),
        telegram_owner_notify_id=op.telegram_owner_notify_id,
        telegram_owner_notify_enabled=op.telegram_owner_notify_enabled,
    )


def create_operacao(db: Session, body: OperacaoCreate) -> OperacaoOut:
    op = Operacao(nome=body.nome.strip())
    db.add(op)
    db.commit()
    db.refresh(op)
    return operacao_to_out(op)


def create_usuario_admin(db: Session, body: UsuarioCreate) -> Usuario:
    if db.scalars(select(Usuario).where(Usuario.email == str(body.email))).first():
        raise ConflictError("E-mail já cadastrado")
    if body.tipo not in (UserRole.ADMIN, UserRole.DONO):
        raise ConflictError("Tipo de usuário inválido")
    if body.tipo == UserRole.DONO and body.operacao_id is None:
        raise ConflictError("Dono exige operacao_id")
    if body.tipo == UserRole.ADMIN and body.operacao_id is not None:
        raise ConflictError("Admin não deve ter operacao_id")
    if body.operacao_id is not None:
        parent = db.get(Operacao, body.operacao_id)
        if not parent:
            raise ConflictError("Operação inexistente")
    user = Usuario(
        email=str(body.email).lower(),
        senha_hash=hash_password(body.password),
        tipo=body.tipo.value,
        operacao_id=body.operacao_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _usuario_to_admin_out(user: Usuario, operacao_nome: str | None = None) -> UserAdminOut:
    return UserAdminOut(
        id=user.id,
        email=user.email,
        tipo=UserRole(user.tipo),
        operacao_id=user.operacao_id,
        created_at=user.created_at,
        operacao_nome=operacao_nome,
    )


def list_usuarios_admin(
    db: Session,
    *,
    tipo: UserRole | None = None,
    operacao_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[UserAdminOut], int]:
    base = select(Usuario, Operacao.nome).outerjoin(Operacao, Usuario.operacao_id == Operacao.id)
    count_q = select(func.count()).select_from(Usuario)
    if tipo is not None:
        base = base.where(Usuario.tipo == tipo.value)
        count_q = count_q.where(Usuario.tipo == tipo.value)
    if operacao_id is not None:
        base = base.where(Usuario.operacao_id == operacao_id)
        count_q = count_q.where(Usuario.operacao_id == operacao_id)
    total = int(db.scalar(count_q) or 0)
    rows = db.execute(base.order_by(Usuario.created_at.desc()).limit(limit).offset(offset)).all()
    items = [_usuario_to_admin_out(user, op_nome) for user, op_nome in rows]
    return items, total


def get_operacao_or_404(db: Session, operacao_id: int) -> Operacao | None:
    return db.get(Operacao, operacao_id)


def list_operacoes(db: Session, user: CurrentUser) -> list[OperacaoOut]:
    if user.role != UserRole.ADMIN:
        raise ForbiddenError("Somente admin")
    rows = list(db.scalars(select(Operacao).order_by(Operacao.id)).all())
    return [operacao_to_out(op) for op in rows]


def get_telegram_template_meta() -> list[dict]:
    return list_template_meta()


def get_custom_message_triggers() -> list[dict]:
    return list_custom_message_triggers()


def preview_telegram_template(
    *,
    key: str | None = None,
    trigger: str | None = None,
    template: str | None = None,
    context: dict | None = None,
) -> str:
    if trigger:
        ctx = context or sample_context_for_key(trigger)
        body = template or ""
        return render_custom_body(body, **ctx)
    assert key is not None
    overrides = {key: template} if template else None
    ctx = context or sample_context_for_key(key)
    return render_template(key, overrides=overrides, **ctx)


def _validate_owner_notify_settings(op: Operacao) -> None:
    if op.telegram_owner_notify_enabled and not (op.telegram_owner_notify_id or "").strip():
        raise MotoPayError("Informe o Telegram ID para ativar notificações ao dono.")


def send_telegram_owner_notify_test(db: Session, operacao_id: int) -> None:
    from motopay.infrastructure.telegram.notify import (
        TelegramPermanentError,
        send_telegram_text,
    )

    op = db.get(Operacao, operacao_id)
    if not op:
        raise NotFoundError("Operação não encontrada")
    _validate_owner_notify_settings(op)
    if not op.telegram_owner_notify_enabled:
        raise MotoPayError("Ative as notificações ao dono antes de enviar o teste.")
    chat_id = (op.telegram_owner_notify_id or "").strip()
    try:
        send_telegram_text(
            chat_id=chat_id,
            text=(
                "✅ Teste MotoPay\n"
                f"Operação: {op.nome}\n"
                "Notificações ao dono estão configuradas corretamente."
            ),
        )
    except TelegramPermanentError as exc:
        raise MotoPayError(f"Não foi possível enviar ao Telegram: {exc}") from exc


def _apply_dono_restrictions(body: OperacaoUpdate) -> OperacaoUpdate:
    return OperacaoUpdate(
        multa_fixa_percentual=body.multa_fixa_percentual,
        juros_diario_percentual=body.juros_diario_percentual,
        telegram_templates=body.telegram_templates,
        telegram_bot_menu_buttons=body.telegram_bot_menu_buttons,
        telegram_owner_notify_id=body.telegram_owner_notify_id,
        telegram_owner_notify_enabled=body.telegram_owner_notify_enabled,
        mercadopago_access_token=body.mercadopago_access_token,
        mercadopago_public_key=body.mercadopago_public_key,
        mercadopago_webhook_secret=body.mercadopago_webhook_secret,
    )


def update_operacao(
    db: Session, operacao_id: int, body: OperacaoUpdate, *, role: UserRole | None = None
) -> OperacaoOut:
    if role == UserRole.DONO:
        body = _apply_dono_restrictions(body)

    op = db.get(Operacao, operacao_id)
    if not op:
        raise NotFoundError("Operação não encontrada")
    fields_set = body.model_fields_set
    if body.nome is not None:
        op.nome = body.nome
    if body.multa_fixa_percentual is not None:
        op.multa_fixa_percentual = body.multa_fixa_percentual
    if body.juros_diario_percentual is not None:
        op.juros_diario_percentual = body.juros_diario_percentual
    if body.telegram_templates is not None:
        op.telegram_templates = merge_template_overrides(
            op.telegram_templates, body.telegram_templates
        )
    if body.telegram_custom_messages is not None:
        validated = validate_custom_messages(
            [m.model_dump() for m in body.telegram_custom_messages]
        )
        op.telegram_custom_messages = validated
    if body.telegram_bot_menu_buttons is not None:
        op.telegram_bot_menu_buttons = validate_bot_menu_buttons(
            [b.model_dump() for b in body.telegram_bot_menu_buttons]
        )
    if "telegram_owner_notify_id" in fields_set:
        op.telegram_owner_notify_id = (body.telegram_owner_notify_id or "").strip() or None
    if "telegram_owner_notify_enabled" in fields_set:
        op.telegram_owner_notify_enabled = bool(body.telegram_owner_notify_enabled)
    _validate_owner_notify_settings(op)
    if body.mercadopago_access_token is not None:
        op.mercadopago_access_token = body.mercadopago_access_token.strip() or None
    if body.mercadopago_public_key is not None:
        op.mercadopago_public_key = body.mercadopago_public_key.strip() or None
    if body.mercadopago_webhook_secret is not None:
        op.mercadopago_webhook_secret = body.mercadopago_webhook_secret.strip() or None
    db.add(op)
    db.commit()
    db.refresh(op)
    return operacao_to_out(op)
