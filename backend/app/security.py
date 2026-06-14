import secrets

from fastapi import Header, HTTPException

from .config import settings


def require_password(x_app_password: str | None = Header(default=None)) -> None:
    """Gate endpoints behind a shared password.

    The frontend sends the password in the X-App-Password header. If
    APP_PASSWORD is unset (local dev), the gate is disabled. Comparison is
    constant-time to avoid leaking the password via timing.
    """
    expected = settings.app_password
    if not expected:
        return
    if not x_app_password or not secrets.compare_digest(x_app_password, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing access password.")
