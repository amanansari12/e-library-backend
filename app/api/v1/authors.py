"""Author catalog routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_admin
from app.schemas.catalog import AuthorCreate, AuthorResponse, AuthorUpdate
from app.services.catalog import CatalogService


router = APIRouter(prefix="/api/v1/authors", tags=["authors"])
catalog_service = CatalogService()


@router.get("", response_model=list[AuthorResponse])
def list_authors(db: Annotated[Session, Depends(get_db)]) -> list[AuthorResponse]:
    return catalog_service.repository.list_authors(db)


@router.get("/{author_id}", response_model=AuthorResponse)
def get_author(author_id: int, db: Annotated[Session, Depends(get_db)]) -> AuthorResponse:
    return catalog_service._require_author(db, author_id)


@router.post("", response_model=AuthorResponse, status_code=status.HTTP_201_CREATED)
def create_author(
    payload: AuthorCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[object, Depends(require_admin)],
) -> AuthorResponse:
    return catalog_service.create_author(db, payload)


@router.patch("/{author_id}", response_model=AuthorResponse)
def update_author(
    author_id: int,
    payload: AuthorUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[object, Depends(require_admin)],
) -> AuthorResponse:
    return catalog_service.update_author(db, author_id, payload)
