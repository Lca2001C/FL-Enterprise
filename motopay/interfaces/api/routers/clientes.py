from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, require_operacional, resolve_operacao_id
from motopay.interfaces.api.pagination import clamp_limit, clamp_offset
from motopay.interfaces.api.schemas import (
    ClienteCreate,
    ClienteMpCardOut,
    ClienteOut,
    ClienteUpdate,
    Paginated,
<<<<<<< HEAD
    SaveClienteCardRequest,
)
from motopay.services.card_payment_service import (
    delete_cliente_card,
    list_cliente_cards,
    save_cliente_card,
=======
    SaveMpCardRequest,
)
from motopay.services.card_payment_service import (
    delete_cliente_mp_card,
    list_cliente_mp_cards,
    save_cliente_mp_card,
    set_default_cliente_mp_card,
>>>>>>> main
)
from motopay.services.fleet_service import (
    create_cliente,
    delete_cliente,
    get_cliente,
    update_cliente,
)
from motopay.services.fleet_service import (
    list_clientes as list_clientes_service,
)

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.get("", response_model=Paginated[ClienteOut])
def list_clientes(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
    q: str | None = Query(default=None),
) -> Paginated[ClienteOut]:
    lim = clamp_limit(limit)
    off = clamp_offset(offset)
    rows, total = list_clientes_service(db, user, operacao_id, limit=lim, offset=off, q=q)
    return Paginated(items=rows, total=total, limit=lim, offset=off)


@router.post("", response_model=ClienteOut)
def create(
    body: ClienteCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> ClienteOut:
    return create_cliente(db, user, operacao_id, body)


@router.get("/{cliente_id}", response_model=ClienteOut)
def get_one(
    cliente_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> ClienteOut:
    return get_cliente(db, user, operacao_id, cliente_id)


@router.patch("/{cliente_id}", response_model=ClienteOut)
def patch(
    cliente_id: int,
    body: ClienteUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> ClienteOut:
    return update_cliente(db, user, operacao_id, cliente_id, body)


<<<<<<< HEAD
@router.get("/{cliente_id}/mercadopago/cards", response_model=list[ClienteMpCardOut])
=======
@router.get("/{cliente_id}/mp-cards", response_model=list[ClienteMpCardOut])
>>>>>>> main
def list_mp_cards(
    cliente_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> list[ClienteMpCardOut]:
<<<<<<< HEAD
    return list_cliente_cards(db, user, operacao_id, cliente_id)


@router.post("/{cliente_id}/mercadopago/cards", response_model=ClienteMpCardOut)
def save_mp_card(
    cliente_id: int,
    body: SaveClienteCardRequest,
=======
    from motopay.services.billing_service import _effective_operacao

    op_id = _effective_operacao(user, operacao_id)
    return list_cliente_mp_cards(db, cliente_id, op_id)


@router.post("/{cliente_id}/mp-cards", response_model=ClienteMpCardOut)
def save_mp_card(
    cliente_id: int,
    body: SaveMpCardRequest,
>>>>>>> main
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> ClienteMpCardOut:
<<<<<<< HEAD
    return save_cliente_card(db, user, operacao_id, cliente_id, card_token=body.card_token)


@router.delete("/{cliente_id}/mercadopago/cards/{card_id}")
def delete_mp_card(
=======
    return save_cliente_mp_card(
        db, user, operacao_id, cliente_id=cliente_id, token=body.token
    )


@router.post("/{cliente_id}/mp-cards/{card_id}/default", response_model=ClienteMpCardOut)
def default_mp_card(
>>>>>>> main
    cliente_id: int,
    card_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
<<<<<<< HEAD
) -> dict[str, str]:
    delete_cliente_card(db, user, operacao_id, cliente_id, card_id)
=======
) -> ClienteMpCardOut:
    return set_default_cliente_mp_card(
        db, user, operacao_id, cliente_id=cliente_id, card_id=card_id
    )


@router.delete("/{cliente_id}/mp-cards/{card_id}")
def remove_mp_card(
    cliente_id: int,
    card_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
):
    delete_cliente_mp_card(db, user, operacao_id, cliente_id=cliente_id, card_id=card_id)
>>>>>>> main
    return {"status": "success"}


@router.delete("/{cliente_id}")
def delete_one(
    cliente_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
):
    delete_cliente(db, user, operacao_id, cliente_id)
    return {"status": "success"}
