from __future__ import annotations

from motopay.domain.enums import UserRole
from motopay.interfaces.api.schemas import OperacaoUpdate, TelegramCustomMessage
from motopay.services.operacao_service import update_operacao

# Formato exigido por is_valid_mp_access_token/is_valid_mp_public_key:
# prefixo APP_USR-/TEST- e no mínimo 20 caracteres.
_FAKE_MP_TOKEN = "TEST-1234567890123456-060119-fake"
_FAKE_MP_PUBLIC_KEY = "TEST-abcdef12-3456-7890-fake"


def test_dono_can_save_mercadopago_credentials(db_session, operacao_a):
    update_operacao(
        db_session,
        operacao_a.id,
        OperacaoUpdate(
            nome="Nome hackeado",
            mercadopago_access_token=_FAKE_MP_TOKEN,
            mercadopago_public_key=_FAKE_MP_PUBLIC_KEY,
            mercadopago_webhook_secret="whsec",
            multa_fixa_percentual=5,
        ),
        role=UserRole.DONO,
    )
    db_session.refresh(operacao_a)
    assert operacao_a.nome == "Operação A"
    assert operacao_a.mercadopago_access_token == _FAKE_MP_TOKEN
    assert operacao_a.mercadopago_public_key == _FAKE_MP_PUBLIC_KEY
    assert operacao_a.mercadopago_webhook_secret == "whsec"
    assert float(operacao_a.multa_fixa_percentual) == 5.0


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
