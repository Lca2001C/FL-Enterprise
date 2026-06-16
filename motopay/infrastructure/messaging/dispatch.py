from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def enqueue_domain_event(ev_id: int | None) -> None:
    """Enfileira o processamento de um evento de domínio sem nunca derrubar o
    request que o originou.

    - Modo degradado (sem Redis / InMemoryRedis): apenas registra e segue — o
      evento fica persistido e será processado quando houver Redis + worker.
    - Broker indisponível (Redis caiu): falha rápida e silenciosa (log), em vez
      de re-tentar a conexão e travar o webhook/endpoint.
    """
    if not ev_id:
        return
    from motopay.infrastructure.redis_client import redis_using_memory

    if redis_using_memory():
        logger.info("domain_event_nao_enfileirado ev_id=%s (modo degradado, sem broker)", ev_id)
        return
    try:
        from motopay.infrastructure.messaging.tasks import handle_domain_event

        handle_domain_event.delay(ev_id)
    except Exception:  # broker fora do ar não pode quebrar o fluxo de pagamento
        logger.exception("falha_ao_enfileirar_domain_event ev_id=%s", ev_id)
