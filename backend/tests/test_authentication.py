import os
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./test-auth.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("AUTH_SECRET", "test-auth-secret-with-at-least-32-bytes")

from app.api.auth import (  # noqa: E402
    _decode_access_token,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.api.routes import dashboard, market, plans, reports, settings, workloads  # noqa: E402
from app.main import app  # noqa: E402


def _user(**kwargs):
    return SimpleNamespace(
        id=kwargs.get("id", 1),
        is_active=kwargs.get("is_active", True),
        tokens_valid_after=kwargs.get("tokens_valid_after"),
    )


class FakeDb:
    def __init__(self, user):
        self.user = user

    def get(self, model, user_id):
        return self.user if self.user and self.user.id == user_id else None


def test_missing_credentials_returns_401():
    with pytest.raises(HTTPException) as error:
        get_current_user(None, FakeDb(_user()))
    assert error.value.status_code == 401
    assert error.value.headers["WWW-Authenticate"] == "Bearer"


def test_invalid_and_expired_tokens_return_401(monkeypatch):
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not-a-token")
    with pytest.raises(HTTPException) as invalid:
        get_current_user(credentials, FakeDb(_user()))
    assert invalid.value.status_code == 401

    token = create_access_token(_user())
    monkeypatch.setattr("app.api.auth.time.time", lambda: 10**12)
    with pytest.raises(HTTPException) as expired:
        get_current_user(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
            FakeDb(_user()),
        )
    assert expired.value.status_code == 401


def test_valid_token_returns_active_user():
    user = _user(id=7)
    token = create_access_token(user)
    assert get_current_user(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
        FakeDb(user),
    ) is user


def test_revoked_token_returns_401():
    user = _user(tokens_valid_after=datetime.now(timezone.utc))
    token = create_access_token(user)
    with pytest.raises(HTTPException) as error:
        get_current_user(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
            FakeDb(user),
        )
    assert error.value.status_code == 401


def test_token_payload_contains_user_id_and_expiration():
    token = create_access_token(_user(id=13))
    user_id, issued_at = _decode_access_token(token)
    assert user_id == 13
    assert issued_at > 0


def test_password_hashing_is_one_way_and_verifiable():
    encoded = hash_password("correct horse battery staple")
    assert encoded != "correct horse battery staple"
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)


def test_feature_routers_require_current_user():
    for router in (dashboard, workloads, reports, settings, market, plans):
        assert any(dependency.dependency is get_current_user for dependency in router.dependencies)


def test_protected_endpoint_rejects_missing_invalid_and_expired_tokens(monkeypatch):
    client = TestClient(app)
    missing = client.get("/api/workloads")
    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"

    invalid = client.get(
        "/api/workloads",
        headers={"Authorization": "Bearer forged-token"},
    )
    assert invalid.status_code == 401

    token = create_access_token(_user())
    monkeypatch.setattr("app.api.auth.time.time", lambda: 10**12)
    expired = client.get(
        "/api/workloads",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert expired.status_code == 401
