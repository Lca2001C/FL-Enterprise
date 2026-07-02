from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from motopay.domain.enums import UserRole
from motopay.domain.exceptions import ConflictError, ForbiddenError, MotoPayError, NotFoundError
from motopay.infrastructure.crypto.token_encryption import encrypt_token
from motopay.infrastructure.db.models import Operacao, Usuario
from motopay.infrastructure.payments.mercadopago_client import (
    is_valid_mp_access_token,
    is_valid_mp_public_key,
)
from motopay.infrastructure.telegram.notify import TelegramPermanentError, send_telegram_text
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
    OperacaoUsuarioCreate,
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


def create_operacao_usuario(
    db: Session, operacao_id: int | None, body: OperacaoUsuarioCreate
) -> Usuario:
    """Cria um usuário (co-DONO) na própria operação. tipo e operacao_id são
    forçados aqui — o DONO só adiciona acessos à própria operação."""
    if operacao_id is None:
        raise ForbiddenError("Operação não definida")
    op = db.get(Operacao, operacao_id)
    if not op:
        raise NotFoundError("Operação não encontrada")
    email = str(body.email).lower()
    if db.scalars(select(Usuario).where(Usuario.email == email)).first():
        raise ConflictError("E-mail já cadastrado")
    user = Usuario(
        email=email,
        senha_hash=hash_password(body.password),
        tipo=UserRole.DONO.value,
        operacao_id=operacao_id,
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


def delete_usuario(db: Session, requester: CurrentUser, usuario_id: int) -> None:
    """Exclui um usuário. Regras:
    - Apenas ADMIN pode chamar esta função.
    - Não é possível excluir o próprio usuário (evita auto-lockout).
    """
    u = db.get(Usuario, usuario_id)
    if not u:
        raise NotFoundError("Usuário não encontrado")
    if u.id == requester.id:
        raise ConflictError("Você não pode excluir seu próprio usuário")
    db.delete(u)
    db.commit()


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
    if key is None:
        raise MotoPayError("Informe key ou trigger para pré-visualização do template")
    overrides = {key: template} if template else None
    ctx = context or sample_context_for_key(key)
    return render_template(key, overrides=overrides, **ctx)


def _validate_owner_notify_settings(op: Operacao) -> None:
    if op.telegram_owner_notify_enabled and not (op.telegram_owner_notify_id or "").strip():
        raise MotoPayError("Informe o Telegram ID para ativar notificações ao dono.")


def send_telegram_owner_notify_test(db: Session, operacao_id: int) -> None:
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


_ALLOWED_DONO_UPDATE_FIELDS = frozenset(
    {
        "multa_fixa_percentual",
        "juros_diario_percentual",
        "telegram_templates",
        "telegram_bot_menu_buttons",
        "telegram_owner_notify_id",
        "telegram_owner_notify_enabled",
    }
)


def _apply_dono_restrictions(body: OperacaoUpdate) -> OperacaoUpdate:
    # Credenciais Mercado Pago NÃO são editáveis pelo dono: a conexão da conta
    # do dono é exclusivamente via OAuth (Ajustes → "Conectar Mercado Pago").
    # Admin segue podendo configurar manualmente (fallback/suporte).
    data = body.model_dump(exclude_unset=True)
    return OperacaoUpdate(
        **{k: v for k, v in data.items() if k in _ALLOWED_DONO_UPDATE_FIELDS}
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
        flag_modified(op, "telegram_templates")
    if body.telegram_custom_messages is not None:
        validated = validate_custom_messages(
            [m.model_dump() for m in body.telegram_custom_messages]
        )
        op.telegram_custom_messages = validated
        flag_modified(op, "telegram_custom_messages")
    if body.telegram_bot_menu_buttons is not None:
        op.telegram_bot_menu_buttons = validate_bot_menu_buttons(
            [b.model_dump() for b in body.telegram_bot_menu_buttons]
        )
        flag_modified(op, "telegram_bot_menu_buttons")
    if "telegram_owner_notify_id" in fields_set:
        op.telegram_owner_notify_id = (body.telegram_owner_notify_id or "").strip() or None
    if "telegram_owner_notify_enabled" in fields_set:
        op.telegram_owner_notify_enabled = bool(body.telegram_owner_notify_enabled)
    _validate_owner_notify_settings(op)
    if body.mercadopago_access_token is not None:
        raw_token = body.mercadopago_access_token.strip() or None
        if raw_token and not is_valid_mp_access_token(raw_token):
            raise MotoPayError(
                "Access Token Mercado Pago inválido. Cole o token completo (APP_USR-... ou TEST-...)."
            )
        op.mercadopago_access_token = encrypt_token(raw_token) if raw_token else None
        if raw_token and op.mercadopago_public_key and not op.mercadopago_oauth_user_id:
            op.mercadopago_connection_status = "connected"
    if body.mercadopago_public_key is not None:
        raw_pk = body.mercadopago_public_key.strip() or None
        if raw_pk and not is_valid_mp_public_key(raw_pk):
            raise MotoPayError(
                "Public Key Mercado Pago inválida. Cole a chave completa (APP_USR-... ou TEST-...)."
            )
        op.mercadopago_public_key = raw_pk
    if body.mercadopago_webhook_secret is not None:
        raw_secret = body.mercadopago_webhook_secret.strip() or None
        if raw_secret is not None and len(raw_secret) < 8:
            raise MotoPayError(
                "Webhook secret muito curto — cole o valor completo gerado no Mercado Pago."
            )
        op.mercadopago_webhook_secret = raw_secret
    db.add(op)
    db.commit()
    db.refresh(op)
    return operacao_to_out(op)
