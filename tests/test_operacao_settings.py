from __future__ import annotations

from motopay.domain.enums import UserRole
from motopay.infrastructure.crypto.token_encryption import decrypt_token
from motopay.infrastructure.telegram.templates import (
    DEFAULT_BOT_MENU_BUTTONS,
    DEFAULT_TELEGRAM_TEMPLATES,
    list_template_meta,
)
from motopay.interfaces.api.schemas import OperacaoUpdate, TelegramCustomMessage
from motopay.services.operacao_service import update_operacao

from tests.conftest import auth_header, login

<<<<<<< HEAD
def test_dono_update_ignores_nome_and_admin_fields(db_session, operacao_a):
=======
# Formato exigido por is_valid_mp_access_token/is_valid_mp_public_key:
# prefixo APP_USR-/TEST- e no mínimo 20 caracteres.
_FAKE_MP_TOKEN = "TEST-1234567890123456-060119-fake"
_FAKE_MP_PUBLIC_KEY = "TEST-abcdef12-3456-7890-fake"


def test_dono_cannot_save_mercadopago_credentials(db_session, operacao_a):
    # Dono conecta o MP exclusivamente via OAuth — credenciais manuais são
    # ignoradas no PATCH (restrição de _apply_dono_restrictions).
>>>>>>> main
    update_operacao(
        db_session,
        operacao_a.id,
        OperacaoUpdate(
            nome="Nome hackeado",
<<<<<<< HEAD
=======
            mercadopago_access_token=_FAKE_MP_TOKEN,
            mercadopago_public_key=_FAKE_MP_PUBLIC_KEY,
            mercadopago_webhook_secret="whsec-12345678",
>>>>>>> main
            multa_fixa_percentual=5,
        ),
        role=UserRole.DONO,
    )
    db_session.refresh(operacao_a)
    assert operacao_a.nome == "Operação A"
<<<<<<< HEAD
    assert float(operacao_a.multa_fixa_percentual) == 5.0


def test_dono_can_save_mercadopago_credentials(db_session, operacao_a):
=======
    assert operacao_a.mercadopago_access_token is None
    assert operacao_a.mercadopago_public_key is None
    assert operacao_a.mercadopago_webhook_secret is None
    assert float(operacao_a.multa_fixa_percentual) == 5.0


def test_admin_can_save_mercadopago_credentials(db_session, operacao_a):
>>>>>>> main
    update_operacao(
        db_session,
        operacao_a.id,
        OperacaoUpdate(
<<<<<<< HEAD
            mercadopago_access_token="op-access",
            mercadopago_public_key="op-public",
            mercadopago_webhook_secret="op-wh",
        ),
        role=UserRole.DONO,
    )
    db_session.refresh(operacao_a)
    assert operacao_a.mercadopago_access_token == "op-access"
    assert operacao_a.mercadopago_public_key == "op-public"
    assert operacao_a.mercadopago_webhook_secret == "op-wh"
=======
            mercadopago_access_token=_FAKE_MP_TOKEN,
            mercadopago_public_key=_FAKE_MP_PUBLIC_KEY,
            mercadopago_webhook_secret="whsec-12345678",
        ),
        role=UserRole.ADMIN,
    )
    db_session.refresh(operacao_a)
    assert decrypt_token(operacao_a.mercadopago_access_token) == _FAKE_MP_TOKEN
    assert operacao_a.mercadopago_public_key == _FAKE_MP_PUBLIC_KEY
    assert operacao_a.mercadopago_webhook_secret == "whsec-12345678"
>>>>>>> main


def test_dono_cannot_save_custom_messages(db_session, operacao_a):
    msg = TelegramCustomMessage(
        id="custom-1",
        label="Pagamento extra",
        trigger="pagamento_confirmado",
        body="Obrigado pelo pagamento!",
        enabled=True,
        replace_default=False,
    )
    out = update_operacao(
        db_session,
        operacao_a.id,
        OperacaoUpdate(telegram_custom_messages=[msg]),
        role=UserRole.DONO,
    )
    assert out.telegram_custom_messages == []


def _frontend_like_template_overrides() -> dict[str, str]:
    """Replica buildTemplateOverrides() do SettingsView: todas as chaves + um override."""
    overrides = {meta["key"]: meta["default"] for meta in list_template_meta()}
    overrides["bot_chat_contact"] = "Resposta customizada de contato para {cliente}."
    overrides["overdue_intro_0"] = "Intro de atraso personalizada pelo dono."
    return overrides


def test_api_dono_save_multa_templates_roundtrip(client, dono_user, operacao_a, db_session) -> None:
    tokens = login(client, "dono@test.local", "donodono")
    headers = auth_header(tokens["access_token"])
    patch_body = {
        "multa_fixa_percentual": 3.5,
        "juros_diario_percentual": 0.15,
        "telegram_templates": _frontend_like_template_overrides(),
        "telegram_bot_menu_buttons": [dict(b) for b in DEFAULT_BOT_MENU_BUTTONS],
        "telegram_owner_notify_enabled": True,
        "telegram_owner_notify_id": "1122334455",
    }
    patch = client.patch("/api/v1/operacoes/me", headers=headers, json=patch_body)
    assert patch.status_code == 200, patch.text

    get = client.get("/api/v1/operacoes/me", headers=headers)
    assert get.status_code == 200, get.text
    data = get.json()
    assert float(data["multa_fixa_percentual"]) == 3.5
    assert float(data["juros_diario_percentual"]) == 0.15
    assert data["telegram_owner_notify_enabled"] is True
    assert data["telegram_owner_notify_id"] == "1122334455"
    assert (
        data["telegram_templates"]["bot_chat_contact"]
        == "Resposta customizada de contato para {cliente}."
    )
    assert data["telegram_templates"]["overdue_intro_0"] == "Intro de atraso personalizada pelo dono."
    assert data["telegram_templates"]["pagamento_confirmado"] == DEFAULT_TELEGRAM_TEMPLATES[
        "pagamento_confirmado"
    ]

    db_session.expire(operacao_a)
    db_session.refresh(operacao_a)
    assert float(operacao_a.multa_fixa_percentual) == 3.5
    assert operacao_a.telegram_templates is not None
    assert (
        operacao_a.telegram_templates["bot_chat_contact"]
        == "Resposta customizada de contato para {cliente}."
    )
    assert operacao_a.telegram_owner_notify_id == "1122334455"


def test_dono_partial_patch_preserves_owner_notify(db_session, operacao_a) -> None:
    update_operacao(
        db_session,
        operacao_a.id,
        OperacaoUpdate(
            telegram_owner_notify_enabled=True,
            telegram_owner_notify_id="9988776655",
        ),
        role=UserRole.DONO,
    )
    update_operacao(
        db_session,
        operacao_a.id,
        OperacaoUpdate(multa_fixa_percentual=7),
        role=UserRole.DONO,
    )
    db_session.refresh(operacao_a)
    assert float(operacao_a.multa_fixa_percentual) == 7.0
    assert operacao_a.telegram_owner_notify_id == "9988776655"
    assert operacao_a.telegram_owner_notify_enabled is True
