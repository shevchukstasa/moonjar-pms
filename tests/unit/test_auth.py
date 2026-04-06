"""Unit tests for authentication — pure logic, NO database.

Tests: password hashing, JWT creation/decoding, lockout check, CSRF generation.
"""
import pytest
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from api.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    check_lockout,
    record_failed_login,
    generate_csrf_token,
    MAX_FAILED_ATTEMPTS,
    LOCKOUT_DURATION_MINUTES,
    ALGORITHM,
)


class TestPasswordHashing:
    """Test bcrypt password hashing and verification."""

    def test_hash_password_returns_bcrypt_string(self):
        """hash_password returns a bcrypt hash starting with $2b$."""
        hashed = hash_password("Moonjar2024!")
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60  # bcrypt always produces 60-char hashes

    def test_verify_password_correct(self):
        """verify_password returns True for correct password."""
        plain = "SecurePass123!"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_password_wrong(self):
        """verify_password returns False for wrong password."""
        hashed = hash_password("CorrectPassword")
        assert verify_password("WrongPassword", hashed) is False

    def test_verify_password_invalid_hash(self):
        """verify_password returns False (not exception) for malformed hash."""
        assert verify_password("anything", "not_a_bcrypt_hash") is False

    def test_different_passwords_different_hashes(self):
        """Same password hashed twice produces different salts/hashes."""
        h1 = hash_password("SamePassword")
        h2 = hash_password("SamePassword")
        assert h1 != h2  # different salts
        # But both verify correctly
        assert verify_password("SamePassword", h1) is True
        assert verify_password("SamePassword", h2) is True


class TestJWTTokens:
    """Test JWT access/refresh token creation and decoding."""

    def test_access_token_contains_role(self):
        """Access token payload includes sub, role, type=access."""
        token = create_access_token(user_id="user-123", role="owner")
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["role"] == "owner"
        assert payload["type"] == "access"
        assert "jti" in payload
        assert "exp" in payload

    def test_refresh_token_type(self):
        """Refresh token has type=refresh and no role field."""
        token = create_refresh_token(user_id="user-456")
        payload = decode_token(token)
        assert payload["sub"] == "user-456"
        assert payload["type"] == "refresh"
        assert "role" not in payload

    def test_access_token_custom_jti(self):
        """Access token respects custom jti."""
        token = create_access_token(user_id="u1", role="admin", jti="custom-jti-123")
        payload = decode_token(token)
        assert payload["jti"] == "custom-jti-123"

    def test_decode_invalid_token_raises(self):
        """Decoding garbage raises an exception."""
        with pytest.raises(Exception):
            decode_token("not.a.valid.jwt.token")

    def test_access_and_refresh_tokens_differ(self):
        """Access and refresh tokens for the same user are different strings."""
        access = create_access_token("u1", "owner")
        refresh = create_refresh_token("u1")
        assert access != refresh


class TestLockout:
    """Test account lockout logic."""

    def test_check_lockout_not_locked(self):
        """No exception when user is not locked."""
        user = SimpleNamespace(locked_until=None)
        # Should not raise
        check_lockout(user)

    def test_check_lockout_expired_lock(self):
        """No exception when lock has expired."""
        user = SimpleNamespace(
            locked_until=datetime.now(timezone.utc) - timedelta(minutes=1)
        )
        check_lockout(user)  # should not raise

    def test_check_lockout_active_lock_raises_423(self):
        """HTTPException 423 when user is actively locked."""
        from fastapi import HTTPException

        user = SimpleNamespace(
            locked_until=datetime.now(timezone.utc) + timedelta(minutes=10)
        )
        with pytest.raises(HTTPException) as exc_info:
            check_lockout(user)
        assert exc_info.value.status_code == 423
        assert "locked" in exc_info.value.detail.lower()

    def test_record_failed_login_increments_count(self):
        """record_failed_login increments failed_login_count."""
        user = SimpleNamespace(failed_login_count=0, locked_until=None)
        mock_db = MagicMock()
        record_failed_login(mock_db, user)
        assert user.failed_login_count == 1
        assert user.locked_until is None  # not yet at max
        mock_db.commit.assert_called_once()

    def test_record_failed_login_locks_at_max(self):
        """Account locks after MAX_FAILED_ATTEMPTS failures."""
        user = SimpleNamespace(
            failed_login_count=MAX_FAILED_ATTEMPTS - 1,
            locked_until=None,
        )
        mock_db = MagicMock()
        record_failed_login(mock_db, user)
        assert user.failed_login_count == MAX_FAILED_ATTEMPTS
        assert user.locked_until is not None
        # Lock should be ~LOCKOUT_DURATION_MINUTES in the future
        assert user.locked_until > datetime.now(timezone.utc)


class TestCSRF:
    """Test CSRF token generation."""

    def test_csrf_token_is_hex_string(self):
        """CSRF token is a hex HMAC string."""
        token = generate_csrf_token("session-id-abc")
        assert isinstance(token, str)
        assert len(token) == 64  # SHA-256 hex digest = 64 chars

    def test_csrf_token_deterministic(self):
        """Same session_id produces the same CSRF token."""
        t1 = generate_csrf_token("fixed-session")
        t2 = generate_csrf_token("fixed-session")
        assert t1 == t2

    def test_csrf_token_differs_per_session(self):
        """Different session IDs produce different CSRF tokens."""
        t1 = generate_csrf_token("session-1")
        t2 = generate_csrf_token("session-2")
        assert t1 != t2
