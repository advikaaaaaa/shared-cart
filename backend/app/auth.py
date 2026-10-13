from __future__ import annotations

import hashlib
import hmac
import os
import time

from fastapi import HTTPException, Request, status

ADMIN_COOKIE = "sharedcart_admin"
ADMIN_SESSION_SECONDS = 8 * 60 * 60


def credentials_configured() -> bool:
    secret = os.getenv("SHAREDCART_ADMIN_SECRET", "")
    return bool(
        os.getenv("SHAREDCART_ADMIN_USERNAME")
        and os.getenv("SHAREDCART_ADMIN_PASSWORD")
        and len(secret) >= 32
    )


def verify_credentials(username: str, password: str) -> bool:
    expected_username = os.getenv("SHAREDCART_ADMIN_USERNAME", "")
    expected_password = os.getenv("SHAREDCART_ADMIN_PASSWORD", "")
    return bool(expected_username and expected_password) and hmac.compare_digest(
        username.encode(), expected_username.encode()
    ) and hmac.compare_digest(password.encode(), expected_password.encode())


def create_admin_session() -> str:
    expires = str(int(time.time()) + ADMIN_SESSION_SECONDS)
    signature = hmac.new(
        os.environ["SHAREDCART_ADMIN_SECRET"].encode(),
        f"admin:{expires}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{expires}.{signature}"


def valid_admin_session(token: str | None) -> bool:
    if not token or not credentials_configured():
        return False
    try:
        expires, supplied = token.split(".", 1)
        if int(expires) < int(time.time()):
            return False
    except (ValueError, TypeError):
        return False
    expected = hmac.new(
        os.environ["SHAREDCART_ADMIN_SECRET"].encode(),
        f"admin:{expires}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(supplied, expected)


def require_admin(request: Request) -> None:
    if not valid_admin_session(request.cookies.get(ADMIN_COOKIE)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin sign-in required",
        )
