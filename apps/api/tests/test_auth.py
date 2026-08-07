"""Authentication and authorization tests."""

from sqlalchemy import func, select

from tests.conftest import TEST_EMAIL, TEST_PASSWORD


def test_login_success_sets_httponly_cookie(client, user):
    res = client.post("/api/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    assert res.status_code == 200
    assert res.json()["email"] == TEST_EMAIL
    cookie = res.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    # test env is not production: Secure flag must appear only in production


def test_login_wrong_password_and_unknown_email_are_indistinguishable(client, user):
    r1 = client.post("/api/auth/login", json={"email": TEST_EMAIL, "password": "wrong"})
    r2 = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
    assert r1.status_code == r2.status_code == 401
    assert r1.json()["detail"] == r2.json()["detail"]


def test_me_requires_session(client):
    assert client.get("/api/auth/me").status_code == 401


def test_logout_revokes_server_side(auth_client):
    assert auth_client.get("/api/auth/me").status_code == 200
    token = auth_client.cookies.get("ill_session")
    auth_client.post("/api/auth/logout")
    # Even replaying the exact old cookie must fail: the session row is gone.
    auth_client.cookies.set("ill_session", token)
    assert auth_client.get("/api/auth/me").status_code == 401


def test_session_token_stored_only_as_hash(client, user, db_session):
    res = client.post("/api/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    raw_token = res.cookies["ill_session"]

    from app.modules.auth.models import AuthSession

    row = db_session.scalar(select(AuthSession))
    assert row is not None
    assert raw_token not in (row.token_hash,)  # raw value never stored
    assert len(row.token_hash) == 64  # sha256 hex


def test_login_rate_limit_locks_after_max_attempts(client, user):
    for _ in range(5):  # LOGIN_MAX_ATTEMPTS=5 in test env
        r = client.post("/api/auth/login", json={"email": TEST_EMAIL, "password": "wrong"})
        assert r.status_code == 401
    # Now even the CORRECT password is refused during lockout.
    r = client.post("/api/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    assert r.status_code == 429


def test_successful_login_clears_failure_slate(client, user, db_session):
    for _ in range(3):
        client.post("/api/auth/login", json={"email": TEST_EMAIL, "password": "wrong"})
    r = client.post("/api/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    assert r.status_code == 200

    from app.modules.auth.models import LoginAttempt

    count = db_session.scalar(select(func.count()).select_from(LoginAttempt))
    assert count == 0


def test_passwords_stored_as_argon2(db_session, user):
    assert user.password_hash.startswith("$argon2id$")
    assert TEST_PASSWORD not in user.password_hash


def test_all_learner_endpoints_require_auth(client):
    """Authorization sweep: every non-auth, non-health route must 401 when
    anonymous — new endpoints can't accidentally ship open."""
    from fastapi.routing import APIRoute

    from app.main import app

    # This FastAPI version wraps include_router() results; walk the original
    # routers to enumerate every APIRoute with its full prefixed path.
    routes: list[APIRoute] = [r for r in app.routes if isinstance(r, APIRoute)]
    for wrapper in app.routes:
        inner = getattr(wrapper, "original_router", None)
        if inner is not None:
            routes.extend(r for r in inner.routes if isinstance(r, APIRoute))

    exempt = {"/api/health", "/api/auth/login", "/api/auth/logout"}
    checked = 0
    for route in routes:
        path = route.path if route.path.startswith("/api") else f"/api{route.path}"
        methods = route.methods or set()
        if path in exempt:
            continue
        method = "GET" if "GET" in methods else "POST"
        # fill parameters with dummies; auth runs before path resolution logic
        url = (
            path.replace("{module}", "x").replace("{lesson}", "x").replace("{name}", "x")
            .replace("{index}", "0")
        )
        res = client.request(method, url, json={} if method == "POST" else None)
        assert res.status_code == 401, f"{method} {path} did not require auth ({res.status_code})"
        checked += 1
    assert checked >= 15  # sanity: the sweep actually covered the API
