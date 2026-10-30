from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..config import settings
from ..db import SessionLocal
from ..models.user import User

PASSWORD_ITERATIONS = 310_000
bearer = HTTPBearer(auto_error=False)


def get_db():
    with SessionLocal() as session:
        yield session


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, PASSWORD_ITERATIONS
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), _unb64(salt), int(iterations)
        )
        return hmac.compare_digest(_b64(actual), expected)
    except (ValueError, TypeError, binascii.Error):
        return False


def create_access_token(user: User) -> str:
    issued_at = int(time.time())
    payload = {
        "sub": str(user.id),
        "iat": issued_at,
        "exp": issued_at + settings.auth_token_ttl_minutes * 60,
    }
    encoded = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(
        settings.auth_secret.encode(), encoded.encode(), hashlib.sha256
    ).digest()
    return f"{encoded}.{_b64(signature)}"


def _decode_access_token(token: str) -> tuple[int, int]:
    try:
        encoded, provided_signature = token.split(".", 1)
        expected_signature = hmac.new(
            settings.auth_secret.encode(), encoded.encode(), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(_b64(expected_signature), provided_signature):
            raise ValueError("invalid signature")
        payload = json.loads(_unb64(encoded))
        if int(payload["exp"]) <= int(time.time()):
            raise ValueError("expired token")
        return int(payload["sub"]), int(payload["iat"])
    except (
        ValueError,
        TypeError,
        KeyError,
        OverflowError,
        UnicodeDecodeError,
        binascii.Error,
        json.JSONDecodeError,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id, issued_at = _decode_access_token(credentials.credentials)
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is unavailable.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.tokens_valid_after is not None:
        valid_after = user.tokens_valid_after.replace(tzinfo=timezone.utc).timestamp()
        if issued_at <= int(valid_after):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token has been revoked.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    return user
