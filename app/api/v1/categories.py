"""Category catalog routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_admin
from app.schemas.catalog import CategoryCreate, CategoryResponse, CategoryUpdate
from app.services.catalog import CatalogService


router = APIRouter(prefix="/api/v1/categories", tags=["categories"])
catalog_service = CatalogService()


@router.get("", response_model=list[CategoryResponse])
def list_categories(db: Annotated[Session, Depends(get_db)]) -> list[CategoryResponse]:
    return catalog_service.repository.list_categories(db)


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category_id: int, db: Annotated[Session, Depends(get_db)]) -> CategoryResponse:
    return catalog_service._require_category(db, category_id)


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[object, Depends(require_admin)],
) -> CategoryResponse:
    return catalog_service.create_category(db, payload)


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[object, Depends(require_admin)],
) -> CategoryResponse:
    return catalog_service.update_category(db, category_id, payload)
