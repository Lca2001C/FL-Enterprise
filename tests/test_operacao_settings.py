from __future__ import annotations

from motopay.domain.enums import PaymentProvider, UserRole
from motopay.interfaces.api.schemas import OperacaoUpdate, TelegramCustomMessage
from motopay.services.operacao_service import update_operacao


def test_dono_update_ignores_payment_provider(db_session, operacao_a):
    update_operacao(
        db_session,
        operacao_a.id,
        OperacaoUpdate(
            nome="Nome hackeado",
            payment_provider=PaymentProvider.MERCADOPAGO,
            mercadopago_access_token="secret",
            multa_fixa_percentual=5,
        ),
        role=UserRole.DONO,
    )
    db_session.refresh(operacao_a)
    assert operacao_a.nome == "Operação A"
    assert operacao_a.payment_provider == "asaas"
    assert operacao_a.mercadopago_access_token is None
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
