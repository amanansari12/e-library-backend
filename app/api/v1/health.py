"""Application health endpoint."""

from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Return a lightweight liveness response without external dependencies."""
    return {"status": "ok"}
