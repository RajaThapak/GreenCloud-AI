import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..config import settings
from ..models.core import User
from .deps import get_db
from .errors import ApiError

_ITER = 200_000
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITER)
    return f"pbkdf2${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _ITER)
        return hmac.compare_digest(calc.hex(), digest)
    except (ValueError, TypeError):
        return False


def make_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": exp}, settings.jwt_secret, algorithm="HS256")


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise ApiError(401, "Please sign in.", "unauthorized")
    try:
        user_id = int(jwt.decode(creds.credentials, settings.jwt_secret, algorithms=["HS256"])["sub"])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise ApiError(401, "Your session has expired. Please sign in again.", "unauthorized") from None
    user = db.get(User, user_id)
    if user is None:
        raise ApiError(401, "Please sign in again.", "unauthorized")
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "Admin":
        raise ApiError(403, "Only admins can do this.", "forbidden")
    return user
