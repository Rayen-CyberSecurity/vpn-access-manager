"""API-key authentication for write endpoints."""

from fastapi import Header, HTTPException, status

from api.config import settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Reject requests with a missing or invalid API key."""

    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key.",
        )
