import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.auth import _enforce_rate_limit
from app.middleware import auth as auth_middleware


class DummyClient:
    host = "127.0.0.1"


def _make_request(path: str = "/api/v1/auth/login") -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "query_string": b"",
        "scheme": "http",
        "server": ("test", 80),
    }
    request = Request(scope)
    request._client = DummyClient()  # type: ignore[attr-defined]
    return request


@pytest.mark.asyncio
async def test_auth_rate_limit_fail_closed_when_redis_unavailable(monkeypatch):
    from app.core.database import redis_db

    monkeypatch.setattr(redis_db, "client", None)
    request = _make_request()

    with pytest.raises(HTTPException) as exc:
        await _enforce_rate_limit(request, bucket="login", limit=5, window_seconds=60)

    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_get_current_user_fail_closed_without_redis(monkeypatch):
    from app.core.database import redis_db

    request = _make_request(path="/api/v1/papers")

    monkeypatch.setattr(redis_db, "client", None)
    monkeypatch.setattr(auth_middleware, "verify_token", lambda _t, _kind: {"sub": "u1", "jti": "j1"})

    class FakeUser:
        id = "u1"
        email = "u@test.com"
        name = "u"
        roles = ["user"]
        email_verified = True
        avatar = None
        created_at = None

    async def _fake_get_user(_user_id: str):
        return FakeUser()

    monkeypatch.setattr(auth_middleware, "get_user_by_id", _fake_get_user)

    with pytest.raises(HTTPException) as exc:
        await auth_middleware.get_current_user(request, token="test-token")

    assert exc.value.status_code == 503
