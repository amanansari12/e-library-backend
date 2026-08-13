"""Authentication routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.schemas.auth import AccessTokenResponse, LoginRequest, RefreshTokenRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.auth import AuthService


router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
auth_service = AuthService()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(get_settings().auth_registration_rate_limit)
def register(request: Request, payload: RegisterRequest, db: Annotated[Session, Depends(get_db)]) -> UserResponse:
    """Register a normal USER account."""
    return auth_service.register(db, payload)


@router.post("/login", response_model=TokenResponse)
@limiter.limit(get_settings().auth_login_rate_limit)
def login(request: Request, payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    """Authenticate credentials and issue access and refresh tokens."""
    user, access_token, refresh_token = auth_service.login(db, payload)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(
    payload: RefreshTokenRequest, db: Annotated[Session, Depends(get_db)]
) -> AccessTokenResponse:
    """Issue a new access token for a valid, unrevoked refresh token."""
    return AccessTokenResponse(access_token=auth_service.refresh_access_token(db, payload.refresh_token))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshTokenRequest, db: Annotated[Session, Depends(get_db)]) -> Response:
    """Revoke a refresh token so it cannot issue additional access tokens."""
    auth_service.logout(db, payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
