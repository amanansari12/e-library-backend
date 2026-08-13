"""Authenticated AI provider health and usage routes."""

from typing import Annotated

from fastapi import APIRouter, Depends
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.summary import AIProviderResponse
from app.services.summary import SummaryService


router = APIRouter(prefix="/api/v1/ai", tags=["ai"])
summary_service = SummaryService()


@router.get("/health", response_model=AIProviderResponse)
def ai_health(
    _: Annotated[User, Depends(get_current_user)],
) -> AIProviderResponse:
    return AIProviderResponse(data=summary_service.health())


@router.get("/usage", response_model=AIProviderResponse)
def ai_usage(
    _: Annotated[User, Depends(get_current_user)],
) -> AIProviderResponse:
    return AIProviderResponse(data=summary_service.usage())
