from datetime import date

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from motopay.domain.enums import AnexoEntidade, MultaStatus
from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, require_operacional, resolve_operacao_id
from motopay.interfaces.api.pagination import clamp_limit, clamp_offset
from motopay.interfaces.api.schemas import (
    AnexoOut,
    MultaCreate,
    MultaOut,
    MultaUpdate,
    Paginated,
)
from motopay.services.anexo_service import (
    delete_anexo,
    get_anexo_bytes,
    list_anexos,
    upload_anexo,
)
from motopay.services.multa_service import (
    create_multa,
    delete_multa,
    get_multa,
    update_multa,
)
from motopay.services.multa_service import (
    list_multas as list_multas_service,
)

router = APIRouter(prefix="/multas", tags=["multas"])

_ENTIDADE = AnexoEntidade.MULTA.value


@router.get("", response_model=Paginated[MultaOut])
def list_multas(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
    status: MultaStatus | None = Query(default=None),
    moto_id: int | None = Query(default=None),
    contrato_id: int | None = Query(default=None),
    q: str | None = Query(default=None),
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
) -> Paginated[MultaOut]:
    lim = clamp_limit(limit)
    off = clamp_offset(offset)
    rows, total = list_multas_service(
        db,
        user,
        operacao_id,
        limit=lim,
        offset=off,
        status=status,
        moto_id=moto_id,
        contrato_id=contrato_id,
        q=q,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
    return Paginated(items=rows, total=total, limit=lim, offset=off)


@router.post("", response_model=MultaOut)
def create(
    body: MultaCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> MultaOut:
    return create_multa(db, user, operacao_id, body)


@router.get("/{multa_id}", response_model=MultaOut)
def get_one(
    multa_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> MultaOut:
    return get_multa(db, user, operacao_id, multa_id)


@router.patch("/{multa_id}", response_model=MultaOut)
def patch(
    multa_id: int,
    body: MultaUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> MultaOut:
    return update_multa(db, user, operacao_id, multa_id, body)


@router.delete("/{multa_id}")
def delete_one(
    multa_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> dict[str, str]:
    delete_multa(db, user, operacao_id, multa_id)
    return {"status": "success"}


@router.get("/{multa_id}/anexos", response_model=list[AnexoOut])
def list_multa_anexos(
    multa_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> list[AnexoOut]:
    m = get_multa(db, user, operacao_id, multa_id)
    return list_anexos(db, m.operacao_id, _ENTIDADE, m.id)


@router.post("/{multa_id}/anexos", response_model=AnexoOut)
async def upload_multa_anexo(
    multa_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
    file: UploadFile = File(...),
) -> AnexoOut:
    m = get_multa(db, user, operacao_id, multa_id)
    return await upload_anexo(
        db,
        operacao_id=m.operacao_id,
        entidade_tipo=_ENTIDADE,
        entidade_id=m.id,
        upload=file,
    )


@router.get("/anexos/{anexo_id}")
def download_multa_anexo(
    anexo_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> Response:
    data, content_type, filename = get_anexo_bytes(db, user, operacao_id, anexo_id)
    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "private, max-age=300",
        },
    )


@router.delete("/anexos/{anexo_id}")
def delete_multa_anexo(
    anexo_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> dict[str, str]:
    delete_anexo(db, user, operacao_id, anexo_id)
    return {"status": "success"}
