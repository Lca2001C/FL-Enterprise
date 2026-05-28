from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from motopay.domain.enums import ContratoStatus
from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, require_operacional, resolve_operacao_id
from motopay.interfaces.api.pagination import clamp_limit, clamp_offset
from motopay.interfaces.api.schemas import ContratoCreate, ContratoOut, ContratoUpdate, Paginated
from motopay.services.contrato_document_service import generate_contrato_pdf
from motopay.services.fleet_service import (
    create_contrato,
    get_contrato,
    update_contrato,
)
from motopay.services.fleet_service import (
    list_contratos as list_contratos_service,
)

router = APIRouter(prefix="/contratos", tags=["contratos"])


@router.get("", response_model=Paginated[ContratoOut])
def list_contratos(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
    com_promessa: bool | None = Query(default=None),
    status: ContratoStatus | None = Query(default=None),
    inadimplente: bool | None = Query(default=None),
    cliente_id: int | None = Query(default=None),
) -> Paginated[ContratoOut]:
    lim = clamp_limit(limit)
    off = clamp_offset(offset)
    rows, total = list_contratos_service(
        db,
        user,
        operacao_id,
        limit=lim,
        offset=off,
        com_promessa=com_promessa,
        status=status,
        inadimplente=inadimplente,
        cliente_id=cliente_id,
    )
    return Paginated(items=rows, total=total, limit=lim, offset=off)


@router.post("", response_model=ContratoOut)
def create(
    body: ContratoCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> ContratoOut:
    return create_contrato(db, user, operacao_id, body)


@router.get("/{contrato_id}", response_model=ContratoOut)
def get_one(
    contrato_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> ContratoOut:
    return get_contrato(db, user, operacao_id, contrato_id)


@router.patch("/{contrato_id}", response_model=ContratoOut)
def patch(
    contrato_id: int,
    body: ContratoUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> ContratoOut:
    return update_contrato(db, user, operacao_id, contrato_id, body)


@router.get("/{contrato_id}/documento")
def download_documento(
    contrato_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> Response:
    pdf_bytes, filename = generate_contrato_pdf(db, user, operacao_id, contrato_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
