from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, require_dono_or_admin, resolve_operacao_id
from motopay.interfaces.api.schemas import AnalyticsSummary, MotoAnalyticsRow, RecentActivityRow
from motopay.services.analytics_service import get_recent_activity, get_summary, moto_ranking

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def analytics_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> AnalyticsSummary:
    return get_summary(db, user, operacao_id)


@router.get("/recent-activity", response_model=list[RecentActivityRow])
def analytics_recent_activity(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> list[RecentActivityRow]:
    return get_recent_activity(db, user, operacao_id)


@router.get("/motos/ranking", response_model=list[MotoAnalyticsRow])
def ranking_motos(
    data_inicio: str = Query(..., description="YYYY-MM-DD"),
    data_fim: str = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> list[MotoAnalyticsRow]:
    from datetime import date as date_type

    di = date_type.fromisoformat(data_inicio)
    df = date_type.fromisoformat(data_fim)
    return moto_ranking(db, user, operacao_id, di, df)
