"""API-key authentication for the write endpoints."""

import secrets

from fastapi import Header, HTTPException, status

from api.config import settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Reject the request unless the X-API-Key header matches.

    secrets.compare_digest instead of == : a plain comparison returns as soon
    as two bytes differ, so its running time leaks how much of the key the
    attacker already guessed. compare_digest takes the same time either way.
    """
    if x_api_key is None or not secrets.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key.",
        )
