"""Administrator-only statistics routes."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_admin
from app.schemas.admin import (
    AdminStatistics,
    HighestRatedBookStatistic,
    PopularBookStatistic,
    PopularCategoryStatistic,
)
from app.services.admin import AdminStatisticsService


router = APIRouter(prefix="/api/v1/admin/statistics", tags=["admin statistics"])
statistics_service = AdminStatisticsService()


@router.get("", response_model=AdminStatistics)
def get_statistics(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[object, Depends(require_admin)],
) -> AdminStatistics:
    return statistics_service.overview(db)


@router.get("/popular-books", response_model=list[PopularBookStatistic])
def get_popular_books(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[object, Depends(require_admin)],
) -> list[PopularBookStatistic]:
    return statistics_service.popular_books(db)


@router.get("/popular-categories", response_model=list[PopularCategoryStatistic])
def get_popular_categories(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[object, Depends(require_admin)],
) -> list[PopularCategoryStatistic]:
    return statistics_service.popular_categories(db)


@router.get("/highest-rated", response_model=list[HighestRatedBookStatistic])
def get_highest_rated(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[object, Depends(require_admin)],
) -> list[HighestRatedBookStatistic]:
    return statistics_service.highest_rated(db)
