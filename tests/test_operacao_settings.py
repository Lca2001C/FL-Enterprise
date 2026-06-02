from __future__ import annotations

from motopay.domain.enums import UserRole
from motopay.interfaces.api.schemas import OperacaoUpdate, TelegramCustomMessage
from motopay.services.operacao_service import update_operacao


def test_dono_update_ignores_nome_and_admin_fields(db_session, operacao_a):
    update_operacao(
        db_session,
        operacao_a.id,
        OperacaoUpdate(
            nome="Nome hackeado",
            multa_fixa_percentual=5,
        ),
        role=UserRole.DONO,
    )
    db_session.refresh(operacao_a)
    assert operacao_a.nome == "Operação A"
    assert float(operacao_a.multa_fixa_percentual) == 5.0


def test_dono_can_save_mercadopago_credentials(db_session, operacao_a):
    update_operacao(
        db_session,
        operacao_a.id,
        OperacaoUpdate(
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
