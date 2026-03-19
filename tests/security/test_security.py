"""
Security tests for Moonjar PMS.

Covers: SQL injection prevention, RBAC enforcement, factory scoping,
HttpOnly cookie flags, CSRF validation, account lockout, password hashing,
JWT token validation/expiry, and rate limiting.
"""

import uuid
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from api.main import app
from api.database import Base, get_db
from api.config import get_settings
from api.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_csrf_token,
    validate_csrf,
    check_lockout,
    record_failed_login,
    reset_failed_logins,
    set_auth_cookies,
    ALGORITHM,
    MAX_FAILED_ATTEMPTS,
    LOCKOUT_DURATION_MINUTES,
)
from api.roles import (
    require_role,
    require_owner,
    require_admin,
    require_management,
    require_quality,
    require_warehouse,
    require_sorting,
    require_purchaser,
)
from api.middleware import CSRFMiddleware, RateLimitMiddleware
from api.models import User, Factory, UserFactory, ActiveSession
from api.enums import UserRole

import jwt as jose_jwt

settings = get_settings()

# ---------------------------------------------------------------------------
# Test-local DB setup (in-process SQLite for unit-level, no real PG needed)
# ---------------------------------------------------------------------------

_SQLITE_URL = "sqlite:///./test_security.db"
_engine = create_engine(_SQLITE_URL, connect_args={"check_same_thread": False})
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(scope="module", autouse=True)
def _create_tables():
    """Create all tables once for the module, drop at the end."""
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)
    import os
    try:
        os.remove("test_security.db")
    except FileNotFoundError:
        pass


@pytest.fixture()
def db():
    """Provide a clean DB session with rollback after each test."""
    connection = _engine.connect()
    transaction = connection.begin()
    session = _TestSession(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db):
    """TestClient with the DB session overridden."""
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_factory(db, name="Bali Factory") -> Factory:
    f = Factory(id=uuid.uuid4(), name=name, location="Bali")
    db.add(f)
    db.flush()
    return f


def _make_user(
    db,
    role: str = "production_manager",
    email: str | None = None,
    password: str = "Str0ng!Pass",
    factory: Factory | None = None,
) -> User:
    uid = uuid.uuid4()
    u = User(
        id=uid,
        email=email or f"user-{uid}@test.local",
        name=f"Test {role}",
        role=role,
        password_hash=hash_password(password),
        is_active=True,
        failed_login_count=0,
    )
    db.add(u)
    db.flush()
    if factory:
        uf = UserFactory(id=uuid.uuid4(), user_id=u.id, factory_id=factory.id)
        db.add(uf)
        db.flush()
    return u


def _make_session(db, user: User, jti: str | None = None) -> ActiveSession:
    jti = jti or str(uuid.uuid4())
    s = ActiveSession(
        id=uuid.uuid4(),
        user_id=user.id,
        token_jti=jti,
        ip_address="127.0.0.1",
        user_agent="pytest",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        revoked=False,
    )
    db.add(s)
    db.flush()
    return s


def _login_cookies(db, user: User, jti: str | None = None) -> dict:
    """Return a dict of cookies that authenticate `user`."""
    jti = jti or str(uuid.uuid4())
    _make_session(db, user, jti=jti)
    role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
    access = create_access_token(str(user.id), role_val, jti)
    csrf = generate_csrf_token(jti)
    return {
        "access_token": access,
        "csrf_token": csrf,
    }


def _auth_client_headers(cookies: dict) -> dict:
    """Build header dict including CSRF for mutating requests."""
    return {"X-CSRF-Token": cookies["csrf_token"]}


# ===================================================================
# 1. PASSWORD HASHING
# ===================================================================

class TestPasswordHashing:
    """Verify bcrypt-based password hashing is correct and secure."""

    def test_hash_is_not_plaintext(self):
        plain = "SuperSecret123!"
        hashed = hash_password(plain)
        assert hashed != plain
        assert hashed.startswith("$2")  # bcrypt prefix

    def test_verify_correct_password(self):
        plain = "SuperSecret123!"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("CorrectPassword")
        assert verify_password("WrongPassword", hashed) is False

    def test_verify_empty_password(self):
        hashed = hash_password("SomePassword")
        assert verify_password("", hashed) is False

    def test_verify_garbage_hash_returns_false(self):
        assert verify_password("anything", "not-a-valid-bcrypt-hash") is False

    def test_different_hashes_for_same_password(self):
        """bcrypt uses random salt, so two hashes of the same input differ."""
        h1 = hash_password("Same")
        h2 = hash_password("Same")
        assert h1 != h2
        assert verify_password("Same", h1) is True
        assert verify_password("Same", h2) is True

    def test_bcrypt_cost_factor(self):
        """Hash should use rounds=12 (present in the hash string)."""
        hashed = hash_password("test")
        # bcrypt hash format: $2b$12$...
        assert "$12$" in hashed


# ===================================================================
# 2. JWT TOKEN CREATION, VALIDATION, AND EXPIRY
# ===================================================================

class TestJWTTokens:
    """Verify JWT creation, decoding, expiry, and type enforcement."""

    def test_access_token_contains_correct_claims(self):
        token = create_access_token("user-123", "owner", jti="jti-abc")
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["role"] == "owner"
        assert payload["jti"] == "jti-abc"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_refresh_token_contains_correct_claims(self):
        token = create_refresh_token("user-456", jti="jti-def")
        payload = decode_token(token)
        assert payload["sub"] == "user-456"
        assert payload["jti"] == "jti-def"
        assert payload["type"] == "refresh"
        assert "role" not in payload

    def test_access_token_expires(self):
        """Token created with 0-second expiry should be invalid immediately."""
        expire = datetime.now(timezone.utc) - timedelta(seconds=5)
        payload = {
            "sub": "user-1",
            "role": "owner",
            "jti": "j1",
            "exp": expire,
            "type": "access",
        }
        token = jose_jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)
        with pytest.raises(Exception):
            decode_token(token)

    def test_tampered_token_rejected(self):
        token = create_access_token("u1", "owner")
        tampered = token[:-4] + "XXXX"
        with pytest.raises(Exception):
            decode_token(tampered)

    def test_token_signed_with_wrong_key_rejected(self):
        payload = {
            "sub": "u1",
            "role": "owner",
            "jti": "j1",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "type": "access",
        }
        token = jose_jwt.encode(payload, "wrong-secret-key", algorithm=ALGORITHM)
        with pytest.raises(Exception):
            decode_token(token)

    def test_decode_with_previous_key(self):
        """If SECRET_KEY_PREVIOUS is set, tokens signed with it are accepted."""
        prev_key = "previous-key-for-rotation"
        payload = {
            "sub": "u1",
            "role": "owner",
            "jti": "j1",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "type": "access",
        }
        token = jose_jwt.encode(payload, prev_key, algorithm=ALGORITHM)
        with patch.object(settings, "SECRET_KEY_PREVIOUS", prev_key):
            result = decode_token(token)
            assert result["sub"] == "u1"

    def test_auto_generated_jti(self):
        """If no jti is given, one should be auto-generated."""
        token = create_access_token("u1", "owner")
        payload = decode_token(token)
        assert payload["jti"]  # non-empty
        assert len(payload["jti"]) == 36  # UUID format


# ===================================================================
# 3. HTTPONLY COOKIE FLAGS
# ===================================================================

class TestHttpOnlyCookies:
    """Verify that auth cookies have proper security attributes."""

    def test_login_sets_httponly_access_token(self, client, db):
        user = _make_user(db, role="owner", email="cookies@test.local")
        resp = client.post(
            "/api/auth/login",
            json={"email": "cookies@test.local", "password": "Str0ng!Pass"},
        )
        assert resp.status_code == 200
        # Parse Set-Cookie headers
        cookie_headers = resp.headers.get_list("set-cookie") if hasattr(resp.headers, "get_list") else [
            v for k, v in resp.headers.multi_items() if k.lower() == "set-cookie"
        ]
        access_cookie = [c for c in cookie_headers if c.startswith("access_token=")]
        refresh_cookie = [c for c in cookie_headers if c.startswith("refresh_token=")]
        csrf_cookie = [c for c in cookie_headers if c.startswith("csrf_token=")]

        # access_token: HttpOnly
        assert len(access_cookie) == 1
        assert "httponly" in access_cookie[0].lower()

        # refresh_token: HttpOnly
        assert len(refresh_cookie) == 1
        assert "httponly" in refresh_cookie[0].lower()

        # csrf_token: NOT HttpOnly (JS needs to read it)
        assert len(csrf_cookie) == 1
        assert "httponly" not in csrf_cookie[0].lower()

    def test_login_sets_secure_flag(self, client, db):
        user = _make_user(db, role="owner", email="secure@test.local")
        resp = client.post(
            "/api/auth/login",
            json={"email": "secure@test.local", "password": "Str0ng!Pass"},
        )
        assert resp.status_code == 200
        cookie_headers = [
            v for k, v in resp.headers.multi_items() if k.lower() == "set-cookie"
        ]
        for cookie in cookie_headers:
            assert "secure" in cookie.lower(), f"Cookie missing Secure flag: {cookie}"

    def test_login_sets_samesite_none(self, client, db):
        user = _make_user(db, role="owner", email="samesite@test.local")
        resp = client.post(
            "/api/auth/login",
            json={"email": "samesite@test.local", "password": "Str0ng!Pass"},
        )
        assert resp.status_code == 200
        cookie_headers = [
            v for k, v in resp.headers.multi_items() if k.lower() == "set-cookie"
        ]
        for cookie in cookie_headers:
            assert "samesite=none" in cookie.lower(), f"Missing SameSite=None: {cookie}"


# ===================================================================
# 4. CSRF PROTECTION
# ===================================================================

class TestCSRFProtection:
    """Test the CSRF double-submit cookie pattern."""

    def test_post_without_csrf_returns_403(self, client, db):
        """Mutating request without CSRF token is rejected."""
        factory = _make_factory(db)
        user = _make_user(db, role="owner", email="csrf-miss@test.local")
        cookies = _login_cookies(db, user)
        # Send POST with auth cookie but no CSRF header
        client.cookies.set("access_token", cookies["access_token"])
        client.cookies.set("csrf_token", cookies["csrf_token"])
        resp = client.post(
            "/api/factories",
            json={"name": "New Factory"},
            # No X-CSRF-Token header
        )
        assert resp.status_code == 403
        assert "CSRF" in resp.json().get("detail", "")

    def test_post_with_wrong_csrf_returns_403(self, client, db):
        """Mismatched CSRF cookie and header is rejected."""
        user = _make_user(db, role="owner", email="csrf-wrong@test.local")
        cookies = _login_cookies(db, user)
        client.cookies.set("access_token", cookies["access_token"])
        client.cookies.set("csrf_token", cookies["csrf_token"])
        resp = client.post(
            "/api/factories",
            json={"name": "New Factory"},
            headers={"X-CSRF-Token": "completely-wrong-token"},
        )
        assert resp.status_code == 403

    def test_post_with_valid_csrf_passes(self, client, db):
        """Matching CSRF cookie and header allows the request through."""
        user = _make_user(db, role="owner", email="csrf-ok@test.local")
        cookies = _login_cookies(db, user)
        client.cookies.set("access_token", cookies["access_token"])
        client.cookies.set("csrf_token", cookies["csrf_token"])
        resp = client.post(
            "/api/factories",
            json={"name": "CSRF Test Factory"},
            headers=_auth_client_headers(cookies),
        )
        # Should pass CSRF check. May be 201 (created) or 422 (validation) --
        # the point is it's NOT 403 CSRF.
        assert resp.status_code != 403

    def test_get_request_bypasses_csrf(self, client, db):
        """GET requests do not require CSRF token."""
        user = _make_user(db, role="owner", email="csrf-get@test.local")
        cookies = _login_cookies(db, user)
        client.cookies.set("access_token", cookies["access_token"])
        resp = client.get("/api/factories")
        # Should not get 403 for CSRF on GET
        assert resp.status_code != 403

    def test_login_endpoint_skips_csrf(self, client, db):
        """Login is in SKIP_PREFIXES and should not require CSRF."""
        user = _make_user(db, role="owner", email="csrf-login@test.local")
        resp = client.post(
            "/api/auth/login",
            json={"email": "csrf-login@test.local", "password": "Str0ng!Pass"},
        )
        # Login should succeed or return 401 (bad creds), NOT 403 CSRF
        assert resp.status_code != 403

    def test_validate_csrf_function_raises_on_mismatch(self):
        """Direct unit test for validate_csrf helper."""
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.cookies = {"csrf_token": "token-a"}
        mock_request.headers = {"X-CSRF-Token": "token-b"}
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            validate_csrf(mock_request)
        assert exc_info.value.status_code == 403

    def test_validate_csrf_function_passes_on_match(self):
        """Direct unit test: matching tokens should not raise."""
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.cookies = {"csrf_token": "same-token"}
        mock_request.headers = {"X-CSRF-Token": "same-token"}
        validate_csrf(mock_request)  # should not raise

    def test_validate_csrf_function_skips_get(self):
        """GET requests should be silently skipped."""
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.cookies = {}
        mock_request.headers = {}
        validate_csrf(mock_request)  # should not raise


# ===================================================================
# 5. ACCOUNT LOCKOUT
# ===================================================================

class TestAccountLockout:
    """Test that accounts lock after MAX_FAILED_ATTEMPTS failed logins."""

    def test_lockout_after_max_attempts(self, db):
        user = _make_user(db, email="lockout@test.local")
        for _ in range(MAX_FAILED_ATTEMPTS):
            record_failed_login(db, user)
        assert user.failed_login_count >= MAX_FAILED_ATTEMPTS
        assert user.locked_until is not None
        assert user.locked_until > datetime.now(timezone.utc)

    def test_check_lockout_raises_423(self, db):
        user = _make_user(db, email="locked@test.local")
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
        db.flush()
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            check_lockout(user)
        assert exc_info.value.status_code == 423
        assert "locked" in exc_info.value.detail.lower()

    def test_check_lockout_passes_when_not_locked(self, db):
        user = _make_user(db, email="notlocked@test.local")
        check_lockout(user)  # should not raise

    def test_check_lockout_passes_after_expiry(self, db):
        user = _make_user(db, email="expired-lock@test.local")
        user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.flush()
        check_lockout(user)  # should not raise — lock expired

    def test_reset_clears_lockout(self, db):
        user = _make_user(db, email="resetlock@test.local")
        for _ in range(MAX_FAILED_ATTEMPTS):
            record_failed_login(db, user)
        assert user.locked_until is not None
        reset_failed_logins(db, user)
        assert user.failed_login_count == 0
        assert user.locked_until is None

    def test_login_endpoint_lockout(self, client, db):
        """Integration: 5 bad logins then locked user gets 423."""
        user = _make_user(db, email="lockout-http@test.local", password="RealPass1!")
        for i in range(MAX_FAILED_ATTEMPTS):
            resp = client.post(
                "/api/auth/login",
                json={"email": "lockout-http@test.local", "password": "wrong"},
            )
            assert resp.status_code == 401

        # Now the account should be locked
        resp = client.post(
            "/api/auth/login",
            json={"email": "lockout-http@test.local", "password": "RealPass1!"},
        )
        assert resp.status_code == 423


# ===================================================================
# 6. RBAC ENFORCEMENT
# ===================================================================

class TestRBACEnforcement:
    """Test that role-based access control is properly enforced on endpoints."""

    # --- require_admin: only owner + administrator ---

    def test_admin_endpoint_allowed_for_owner(self, client, db):
        user = _make_user(db, role="owner", email="rbac-owner@test.local")
        cookies = _login_cookies(db, user)
        client.cookies.set("access_token", cookies["access_token"])
        client.cookies.set("csrf_token", cookies["csrf_token"])
        resp = client.post(
            "/api/factories",
            json={"name": "Owner Factory"},
            headers=_auth_client_headers(cookies),
        )
        assert resp.status_code != 403

    def test_admin_endpoint_allowed_for_administrator(self, client, db):
        user = _make_user(db, role="administrator", email="rbac-admin@test.local")
        cookies = _login_cookies(db, user)
        client.cookies.set("access_token", cookies["access_token"])
        client.cookies.set("csrf_token", cookies["csrf_token"])
        resp = client.post(
            "/api/factories",
            json={"name": "Admin Factory"},
            headers=_auth_client_headers(cookies),
        )
        assert resp.status_code != 403

    def test_admin_endpoint_denied_for_ceo(self, client, db):
        user = _make_user(db, role="ceo", email="rbac-ceo@test.local")
        cookies = _login_cookies(db, user)
        client.cookies.set("access_token", cookies["access_token"])
        client.cookies.set("csrf_token", cookies["csrf_token"])
        resp = client.post(
            "/api/factories",
            json={"name": "CEO Factory"},
            headers=_auth_client_headers(cookies),
        )
        assert resp.status_code == 403

    def test_admin_endpoint_denied_for_production_manager(self, client, db):
        user = _make_user(db, role="production_manager", email="rbac-pm@test.local")
        cookies = _login_cookies(db, user)
        client.cookies.set("access_token", cookies["access_token"])
        client.cookies.set("csrf_token", cookies["csrf_token"])
        resp = client.post(
            "/api/factories",
            json={"name": "PM Factory"},
            headers=_auth_client_headers(cookies),
        )
        assert resp.status_code == 403

    def test_admin_endpoint_denied_for_warehouse(self, client, db):
        user = _make_user(db, role="warehouse", email="rbac-wh@test.local")
        cookies = _login_cookies(db, user)
        client.cookies.set("access_token", cookies["access_token"])
        client.cookies.set("csrf_token", cookies["csrf_token"])
        resp = client.post(
            "/api/factories",
            json={"name": "WH Factory"},
            headers=_auth_client_headers(cookies),
        )
        assert resp.status_code == 403

    def test_admin_endpoint_denied_for_sorter_packer(self, client, db):
        user = _make_user(db, role="sorter_packer", email="rbac-sp@test.local")
        cookies = _login_cookies(db, user)
        client.cookies.set("access_token", cookies["access_token"])
        client.cookies.set("csrf_token", cookies["csrf_token"])
        resp = client.post(
            "/api/factories",
            json={"name": "SP Factory"},
            headers=_auth_client_headers(cookies),
        )
        assert resp.status_code == 403

    def test_admin_endpoint_denied_for_purchaser(self, client, db):
        user = _make_user(db, role="purchaser", email="rbac-purch@test.local")
        cookies = _login_cookies(db, user)
        client.cookies.set("access_token", cookies["access_token"])
        client.cookies.set("csrf_token", cookies["csrf_token"])
        resp = client.post(
            "/api/factories",
            json={"name": "Purchaser Factory"},
            headers=_auth_client_headers(cookies),
        )
        assert resp.status_code == 403

    def test_admin_endpoint_denied_for_quality_manager(self, client, db):
        user = _make_user(db, role="quality_manager", email="rbac-qm@test.local")
        cookies = _login_cookies(db, user)
        client.cookies.set("access_token", cookies["access_token"])
        client.cookies.set("csrf_token", cookies["csrf_token"])
        resp = client.post(
            "/api/factories",
            json={"name": "QM Factory"},
            headers=_auth_client_headers(cookies),
        )
        assert resp.status_code == 403

    # --- require_role unit tests ---

    def test_require_role_rejects_unauthorized(self):
        """Unit test: require_role dependency raises 403 for wrong role."""
        dep = require_role("owner", "administrator")
        mock_user = MagicMock()
        mock_user.role = "warehouse"
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            import asyncio
            asyncio.get_event_loop().run_until_complete(dep(mock_user))
        assert exc_info.value.status_code == 403

    def test_require_role_allows_authorized(self):
        """Unit test: require_role dependency passes for allowed role."""
        dep = require_role("owner", "administrator")
        mock_user = MagicMock()
        mock_user.role = "owner"
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(dep(mock_user))
        assert result is mock_user

    # --- Unauthenticated access ---

    def test_protected_endpoint_returns_401_without_auth(self, client):
        """Endpoints requiring auth should return 401 with no token."""
        resp = client.get("/api/factories")
        assert resp.status_code == 401

    def test_protected_endpoint_returns_401_with_invalid_token(self, client):
        """Invalid JWT should return 401."""
        client.cookies.set("access_token", "not.a.valid.jwt.token")
        resp = client.get("/api/factories")
        assert resp.status_code == 401


# ===================================================================
# 7. FACTORY SCOPING
# ===================================================================

class TestFactoryScoping:
    """Test that non-admin users only see data from their assigned factories."""

    def test_apply_factory_filter_admin_sees_all(self, db):
        """Owner/CEO/admin users bypass factory filtering."""
        from api.auth import apply_factory_filter

        f1 = _make_factory(db, name="Factory A")
        f2 = _make_factory(db, name="Factory B")
        admin_user = _make_user(db, role="administrator", email="scope-admin@test.local")

        query = db.query(Factory)
        filtered = apply_factory_filter(query, admin_user, None, Factory)
        results = filtered.all()
        factory_names = {f.name for f in results}
        assert "Factory A" in factory_names
        assert "Factory B" in factory_names

    def test_apply_factory_filter_owner_sees_all(self, db):
        from api.auth import apply_factory_filter

        _make_factory(db, name="Factory X")
        _make_factory(db, name="Factory Y")
        owner_user = _make_user(db, role="owner", email="scope-owner@test.local")

        query = db.query(Factory)
        filtered = apply_factory_filter(query, owner_user, None, Factory)
        results = filtered.all()
        assert len(results) >= 2

    def test_apply_factory_filter_ceo_sees_all(self, db):
        from api.auth import apply_factory_filter

        _make_factory(db, name="Factory M")
        _make_factory(db, name="Factory N")
        ceo_user = _make_user(db, role="ceo", email="scope-ceo@test.local")

        query = db.query(Factory)
        filtered = apply_factory_filter(query, ceo_user, None, Factory)
        results = filtered.all()
        assert len(results) >= 2

    def test_apply_factory_filter_pm_sees_only_assigned(self, db):
        """Production manager with 1 factory assignment sees only that factory."""
        from api.auth import apply_factory_filter

        f1 = _make_factory(db, name="PM Assigned")
        f2 = _make_factory(db, name="PM Not Assigned")
        pm_user = _make_user(
            db, role="production_manager", email="scope-pm@test.local", factory=f1,
        )

        query = db.query(Factory)
        filtered = apply_factory_filter(query, pm_user, None, Factory)
        results = filtered.all()
        factory_ids = {f.id for f in results}
        assert f1.id in factory_ids
        assert f2.id not in factory_ids

    def test_apply_factory_filter_explicit_factory_id(self, db):
        """Explicit factory_id param always filters to that factory."""
        from api.auth import apply_factory_filter

        f1 = _make_factory(db, name="Explicit F1")
        f2 = _make_factory(db, name="Explicit F2")
        admin_user = _make_user(db, role="administrator", email="scope-explicit@test.local")

        query = db.query(Factory)
        filtered = apply_factory_filter(query, admin_user, str(f1.id), Factory)
        results = filtered.all()
        assert len(results) == 1
        assert results[0].id == f1.id

    def test_apply_factory_filter_worker_no_assignments_sees_all(self, db):
        """Worker without any factory assignments sees all (graceful default)."""
        from api.auth import apply_factory_filter

        _make_factory(db, name="Unassigned F1")
        _make_factory(db, name="Unassigned F2")
        # Create user WITHOUT factory assignment
        worker = _make_user(db, role="warehouse", email="scope-nofactory@test.local")

        # Mock user_factories as empty list
        worker.user_factories = []

        query = db.query(Factory)
        filtered = apply_factory_filter(query, worker, None, Factory)
        results = filtered.all()
        assert len(results) >= 2


# ===================================================================
# 8. SQL INJECTION PREVENTION
# ===================================================================

class TestSQLInjection:
    """Verify that common SQL injection payloads are harmless."""

    SQL_PAYLOADS = [
        "'; DROP TABLE users; --",
        "' OR '1'='1",
        "' UNION SELECT * FROM users --",
        "1; DELETE FROM factories",
        "admin'--",
        "' OR 1=1 --",
        "'; INSERT INTO users (email) VALUES ('hacker@evil.com'); --",
        "Robert'); DROP TABLE users;--",
    ]

    def test_login_email_injection(self, client, db):
        """SQL injection in login email field should not cause data leak or crash."""
        _make_user(db, role="owner", email="safe@test.local")
        for payload in self.SQL_PAYLOADS:
            resp = client.post(
                "/api/auth/login",
                json={"email": payload, "password": "anything"},
            )
            # Should return 401 (not found) or 422 (validation), never 500
            assert resp.status_code in (401, 422), (
                f"Unexpected status {resp.status_code} for injection payload: {payload}"
            )

    def test_search_param_injection(self, client, db):
        """SQL injection in query parameters should be safe."""
        user = _make_user(db, role="owner", email="sqli-search@test.local")
        cookies = _login_cookies(db, user)
        client.cookies.set("access_token", cookies["access_token"])
        client.cookies.set("csrf_token", cookies["csrf_token"])
        for payload in self.SQL_PAYLOADS:
            resp = client.get(
                "/api/factories",
                params={"search": payload},
            )
            # Should return normally (200) or 422, never 500
            assert resp.status_code in (200, 422), (
                f"Unexpected status {resp.status_code} for injection payload: {payload}"
            )

    def test_path_param_injection(self, client, db):
        """SQL injection in path parameters (UUIDs) should be rejected."""
        user = _make_user(db, role="owner", email="sqli-path@test.local")
        cookies = _login_cookies(db, user)
        client.cookies.set("access_token", cookies["access_token"])
        for payload in ["'; DROP TABLE factories;--", "1 OR 1=1"]:
            resp = client.get(f"/api/factories/{payload}")
            # FastAPI validates UUID path params, should return 422
            assert resp.status_code == 422

    def test_sqlalchemy_uses_parameterized_queries(self):
        """Verify SQLAlchemy query compilation uses bind parameters."""
        from sqlalchemy import select
        stmt = select(User).where(User.email == "test'; DROP TABLE users;--")
        compiled = stmt.compile(compile_kwargs={"literal_binds": False})
        sql_str = str(compiled)
        # The malicious value should NOT appear literally in the SQL
        assert "DROP TABLE" not in sql_str
        # There should be a bind parameter placeholder
        assert ":email" in sql_str or "?" in sql_str


# ===================================================================
# 9. AUTHENTICATION FLOW — SESSION AND TOKEN LIFECYCLE
# ===================================================================

class TestAuthenticationFlow:
    """Test login, token issuance, session tracking, and logout."""

    def test_successful_login_returns_token_and_user(self, client, db):
        _make_user(db, role="owner", email="flow@test.local", password="GoodPass1!")
        resp = client.post(
            "/api/auth/login",
            json={"email": "flow@test.local", "password": "GoodPass1!"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["user"]["email"] == "flow@test.local"
        assert body["user"]["role"] == "owner"

    def test_login_with_wrong_password(self, client, db):
        _make_user(db, role="owner", email="wrongpw@test.local", password="RealPass!")
        resp = client.post(
            "/api/auth/login",
            json={"email": "wrongpw@test.local", "password": "WrongPass!"},
        )
        assert resp.status_code == 401

    def test_login_with_nonexistent_email(self, client, db):
        resp = client.post(
            "/api/auth/login",
            json={"email": "nobody@test.local", "password": "anything"},
        )
        assert resp.status_code == 401

    def test_get_me_requires_auth(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_get_me_with_valid_token(self, client, db):
        user = _make_user(db, role="owner", email="me@test.local")
        cookies = _login_cookies(db, user)
        client.cookies.set("access_token", cookies["access_token"])
        resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        assert resp.json()["email"] == "me@test.local"

    def test_revoked_session_denies_access(self, client, db):
        """If the session is revoked in DB, the token should be rejected."""
        user = _make_user(db, role="owner", email="revoked@test.local")
        jti = str(uuid.uuid4())
        session = _make_session(db, user, jti=jti)
        session.revoked = True
        db.flush()

        role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
        access = create_access_token(str(user.id), role_val, jti)
        client.cookies.set("access_token", access)
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_inactive_user_denied(self, client, db):
        """Deactivated users should be rejected even with valid token."""
        user = _make_user(db, role="owner", email="inactive@test.local")
        user.is_active = False
        db.flush()
        cookies = _login_cookies(db, user)
        client.cookies.set("access_token", cookies["access_token"])
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_refresh_token_not_accepted_as_access(self, client, db):
        """A refresh token used as access_token should be rejected."""
        user = _make_user(db, role="owner", email="refresh-abuse@test.local")
        jti = str(uuid.uuid4())
        _make_session(db, user, jti=jti)
        refresh = create_refresh_token(str(user.id), jti)
        client.cookies.set("access_token", refresh)
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401


# ===================================================================
# 10. RATE LIMITING
# ===================================================================

class TestRateLimiting:
    """Test the in-memory rate limiter middleware."""

    def test_rate_limiter_classifies_login(self):
        """Login POST is classified as 'login' tier."""
        middleware = RateLimitMiddleware(app)
        mock_request = MagicMock()
        mock_request.url.path = "/api/auth/login"
        mock_request.method = "POST"
        assert middleware._classify(mock_request) == "login"

    def test_rate_limiter_classifies_api(self):
        """General API request is classified as 'api' tier."""
        middleware = RateLimitMiddleware(app)
        mock_request = MagicMock()
        mock_request.url.path = "/api/orders"
        mock_request.method = "GET"
        assert middleware._classify(mock_request) == "api"

    def test_rate_limiter_classifies_webhook(self):
        """Webhook POST is classified as 'webhook' tier."""
        middleware = RateLimitMiddleware(app)
        mock_request = MagicMock()
        mock_request.url.path = "/api/integration/webhook/sales"
        mock_request.method = "POST"
        assert middleware._classify(mock_request) == "webhook"

    def test_rate_limiter_classifies_upload(self):
        """Upload POST is classified as 'upload' tier."""
        middleware = RateLimitMiddleware(app)
        mock_request = MagicMock()
        mock_request.url.path = "/api/packing-photos"
        mock_request.method = "POST"
        assert middleware._classify(mock_request) == "upload"

    def test_rate_limiter_non_api_returns_none(self):
        """Non-API paths are not rate-limited."""
        middleware = RateLimitMiddleware(app)
        mock_request = MagicMock()
        mock_request.url.path = "/some/other/path"
        mock_request.method = "GET"
        assert middleware._classify(mock_request) is None

    def test_login_rate_limit_exceeded(self, client, db):
        """6th login attempt in 1 minute should return 429."""
        _make_user(db, role="owner", email="ratelimit@test.local")

        # Reset the rate limit buckets for a clean test
        for mw in app.user_middleware:
            if hasattr(mw, 'cls') and mw.cls is RateLimitMiddleware:
                break

        # The RateLimitMiddleware is in the app middleware stack.
        # We send 5 login attempts (within the limit) then a 6th.
        # Note: each wrong login also triggers account lockout, so we use
        # unique emails to avoid lockout interference.
        for i in range(6):
            unique_email = f"ratelimit-{i}@test.local"
            _make_user(db, role="owner", email=unique_email)

        responses = []
        for i in range(6):
            resp = client.post(
                "/api/auth/login",
                json={"email": f"ratelimit-{i}@test.local", "password": "wrong"},
            )
            responses.append(resp.status_code)

        # The 6th request (index 5) should be rate-limited
        assert 429 in responses, (
            f"Expected 429 in responses, got: {responses}"
        )

    def test_rate_limit_tiers_have_correct_limits(self):
        """Verify the tier configuration constants."""
        assert RateLimitMiddleware.TIERS["login"]["max"] == 5
        assert RateLimitMiddleware.TIERS["login"]["window"] == 60
        assert RateLimitMiddleware.TIERS["api"]["max"] == 100
        assert RateLimitMiddleware.TIERS["api"]["window"] == 60
        assert RateLimitMiddleware.TIERS["webhook"]["max"] == 30
        assert RateLimitMiddleware.TIERS["upload"]["max"] == 10


# ===================================================================
# 11. CSRF MIDDLEWARE SKIP PREFIXES
# ===================================================================

class TestCSRFSkipPrefixes:
    """Verify that CSRF skip list covers the right paths."""

    def test_skip_prefixes_include_auth_login(self):
        assert "/api/auth/login" in CSRFMiddleware.SKIP_PREFIXES

    def test_skip_prefixes_include_auth_google(self):
        assert "/api/auth/google" in CSRFMiddleware.SKIP_PREFIXES

    def test_skip_prefixes_include_auth_refresh(self):
        assert "/api/auth/refresh" in CSRFMiddleware.SKIP_PREFIXES

    def test_skip_prefixes_include_auth_logout(self):
        assert "/api/auth/logout" in CSRFMiddleware.SKIP_PREFIXES

    def test_skip_prefixes_include_health(self):
        assert "/api/health" in CSRFMiddleware.SKIP_PREFIXES

    def test_skip_prefixes_include_webhooks(self):
        has_integration = any(
            p.startswith("/api/integration") for p in CSRFMiddleware.SKIP_PREFIXES
        )
        assert has_integration

    def test_regular_api_not_in_skip_prefixes(self):
        """Standard API paths like /api/factories should NOT be skipped."""
        for prefix in CSRFMiddleware.SKIP_PREFIXES:
            assert not "/api/factories".startswith(prefix)


# ===================================================================
# 12. CSRF TOKEN GENERATION
# ===================================================================

class TestCSRFTokenGeneration:
    """Verify HMAC-based CSRF token generation."""

    def test_csrf_token_deterministic_for_same_session(self):
        token1 = generate_csrf_token("session-123")
        token2 = generate_csrf_token("session-123")
        assert token1 == token2

    def test_csrf_token_different_for_different_sessions(self):
        token1 = generate_csrf_token("session-aaa")
        token2 = generate_csrf_token("session-bbb")
        assert token1 != token2

    def test_csrf_token_is_hex_string(self):
        token = generate_csrf_token("any-session")
        assert all(c in "0123456789abcdef" for c in token)
        # SHA-256 produces 64 hex characters
        assert len(token) == 64


# ===================================================================
# 13. SESSION MANAGEMENT
# ===================================================================

class TestSessionManagement:
    """Test active session creation, limits, and revocation."""

    def test_session_created_on_login(self, client, db):
        _make_user(db, role="owner", email="sess-create@test.local", password="Pass1!")
        resp = client.post(
            "/api/auth/login",
            json={"email": "sess-create@test.local", "password": "Pass1!"},
        )
        assert resp.status_code == 200
        sessions = db.query(ActiveSession).filter(
            ActiveSession.revoked == False,
        ).all()
        assert len(sessions) >= 1

    def test_max_sessions_evicts_oldest(self, db):
        """Creating > MAX_SESSIONS_PER_USER sessions revokes the oldest."""
        from api.auth import create_session, MAX_SESSIONS_PER_USER
        user = _make_user(db, role="owner", email="sess-max@test.local")

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers = {"user-agent": "test"}

        jtis = []
        for i in range(MAX_SESSIONS_PER_USER + 1):
            jti = str(uuid.uuid4())
            jtis.append(jti)
            create_session(db, str(user.id), jti, mock_request)

        active = db.query(ActiveSession).filter(
            ActiveSession.user_id == user.id,
            ActiveSession.revoked == False,
        ).count()
        assert active <= MAX_SESSIONS_PER_USER


# ===================================================================
# 14. ROLE DEFINITIONS ACCURACY
# ===================================================================

class TestRoleDefinitions:
    """Verify the convenience role shortcuts match their expected role sets."""

    def test_require_owner_only_allows_owner(self):
        # require_owner = require_role("owner")
        dep = require_owner
        mock_user = MagicMock()
        mock_user.role = "administrator"
        from fastapi import HTTPException
        import asyncio
        with pytest.raises(HTTPException):
            asyncio.get_event_loop().run_until_complete(dep(mock_user))

    def test_require_admin_allows_owner_and_admin(self):
        dep = require_admin
        import asyncio
        for role in ["owner", "administrator"]:
            mock_user = MagicMock()
            mock_user.role = role
            result = asyncio.get_event_loop().run_until_complete(dep(mock_user))
            assert result is mock_user

    def test_require_management_roles(self):
        dep = require_management
        import asyncio
        allowed = ["owner", "administrator", "ceo", "production_manager"]
        denied = ["quality_manager", "warehouse", "sorter_packer", "purchaser"]
        for role in allowed:
            mock_user = MagicMock()
            mock_user.role = role
            result = asyncio.get_event_loop().run_until_complete(dep(mock_user))
            assert result is mock_user
        for role in denied:
            mock_user = MagicMock()
            mock_user.role = role
            from fastapi import HTTPException
            with pytest.raises(HTTPException):
                asyncio.get_event_loop().run_until_complete(dep(mock_user))

    def test_require_quality_roles(self):
        dep = require_quality
        import asyncio
        for role in ["owner", "administrator", "quality_manager"]:
            mock_user = MagicMock()
            mock_user.role = role
            result = asyncio.get_event_loop().run_until_complete(dep(mock_user))
            assert result is mock_user

    def test_require_warehouse_roles(self):
        dep = require_warehouse
        import asyncio
        for role in ["owner", "administrator", "warehouse"]:
            mock_user = MagicMock()
            mock_user.role = role
            result = asyncio.get_event_loop().run_until_complete(dep(mock_user))
            assert result is mock_user

    def test_require_sorting_roles(self):
        dep = require_sorting
        import asyncio
        for role in ["owner", "administrator", "production_manager", "sorter_packer"]:
            mock_user = MagicMock()
            mock_user.role = role
            result = asyncio.get_event_loop().run_until_complete(dep(mock_user))
            assert result is mock_user

    def test_require_purchaser_roles(self):
        dep = require_purchaser
        import asyncio
        for role in ["owner", "administrator", "purchaser"]:
            mock_user = MagicMock()
            mock_user.role = role
            result = asyncio.get_event_loop().run_until_complete(dep(mock_user))
            assert result is mock_user


# ===================================================================
# 15. SECURITY HEADERS AND RESPONSE BEHAVIOR
# ===================================================================

class TestSecurityHeaders:
    """Test CSRF token echo and response header behavior."""

    def test_csrf_token_echoed_in_response_header(self, client, db):
        """Middleware should echo csrf_token cookie as X-CSRF-Token header."""
        user = _make_user(db, role="owner", email="echo-csrf@test.local")
        cookies = _login_cookies(db, user)
        client.cookies.set("access_token", cookies["access_token"])
        client.cookies.set("csrf_token", cookies["csrf_token"])
        resp = client.get("/api/factories")
        # The middleware should echo the CSRF token
        assert resp.headers.get("X-CSRF-Token") == cookies["csrf_token"]

    def test_login_response_includes_csrf_header(self, client, db):
        """Login response should include X-CSRF-Token header for frontend."""
        _make_user(db, role="owner", email="login-csrf-hdr@test.local", password="Pass1!")
        resp = client.post(
            "/api/auth/login",
            json={"email": "login-csrf-hdr@test.local", "password": "Pass1!"},
        )
        assert resp.status_code == 200
        assert resp.headers.get("X-CSRF-Token")
