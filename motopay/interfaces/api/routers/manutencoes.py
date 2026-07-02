from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from motopay.domain.enums import ManutencaoCausa, ManutencaoTipo
from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, require_operacional, resolve_operacao_id
from motopay.interfaces.api.pagination import clamp_limit, clamp_offset
from motopay.interfaces.api.schemas import (
    ManutencaoCreate,
    ManutencaoOut,
    ManutencaoResumoOut,
    ManutencaoUpdate,
    Paginated,
)
from motopay.services.manutencao_service import (
    create_manutencao,
    delete_manutencao,
    list_manutencoes,
    resumo_manutencoes,
    update_manutencao,
)

router = APIRouter(prefix="/manutencoes", tags=["manutencoes"])


@router.get("", response_model=Paginated[ManutencaoOut])
def list_rows(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
    tipo: ManutencaoTipo | None = Query(default=None),
    causa: ManutencaoCausa | None = Query(default=None),
    moto_id: int | None = Query(default=None),
    q: str | None = Query(default=None),
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
) -> Paginated[ManutencaoOut]:
    lim = clamp_limit(limit)
    off = clamp_offset(offset)
    rows, total = list_manutencoes(
        db,
        user,
        operacao_id,
        limit=lim,
        offset=off,
        tipo=tipo,
        causa=causa,
        moto_id=moto_id,
        q=q,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
    return Paginated(items=rows, total=total, limit=lim, offset=off)


@router.get("/resumo", response_model=ManutencaoResumoOut)
def resumo(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
    tipo: ManutencaoTipo | None = Query(default=None),
    causa: ManutencaoCausa | None = Query(default=None),
    moto_id: int | None = Query(default=None),
    q: str | None = Query(default=None),
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
) -> ManutencaoResumoOut:
    return resumo_manutencoes(
        db,
        user,
        operacao_id,
        tipo=tipo,
        causa=causa,
        moto_id=moto_id,
        q=q,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )


@router.post("", response_model=ManutencaoOut)
def create(
    body: ManutencaoCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> ManutencaoOut:
    return create_manutencao(db, user, operacao_id, body)


@router.patch("/{manutencao_id}", response_model=ManutencaoOut)
def patch(
    manutencao_id: int,
    body: ManutencaoUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> ManutencaoOut:
    return update_manutencao(db, user, operacao_id, manutencao_id, body)


@router.delete("/{manutencao_id}")
def delete_one(
    manutencao_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> dict[str, str]:
    delete_manutencao(db, user, operacao_id, manutencao_id)
    return {"status": "success"}
