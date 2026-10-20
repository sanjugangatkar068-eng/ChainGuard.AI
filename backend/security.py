"""Optional API-key protection for mutating endpoints.

If ``API_KEY`` is set in the environment, every mutating request must carry a
matching ``X-API-Key`` header. If it is unset (the default), the API is open —
convenient for local demos, but it must not be exposed publicly without a key.

The comparison uses :func:`secrets.compare_digest` so it is not vulnerable to
timing analysis.
"""

import os
import secrets

from fastapi import Header, HTTPException


def configured_key() -> str:
    return (os.getenv("API_KEY", "") or "").strip()


def auth_enabled() -> bool:
    return bool(configured_key())


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """FastAPI dependency: enforce the API key when one is configured."""
    expected = configured_key()
    if not expected:
        return

    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "X-API-Key"},
        )
