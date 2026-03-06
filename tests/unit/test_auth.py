"""Unit tests for authentication."""
import pytest


class TestAuth:
    def test_login_success(self, client):
        """Test successful email/password login."""
        # TODO: implement
        pass

    def test_login_wrong_password(self, client):
        """Test login with wrong password returns 401."""
        # TODO: implement
        pass

    def test_login_lockout_after_5_attempts(self, client):
        """Test account lockout after 5 failed attempts."""
        # TODO: implement
        pass

    def test_refresh_token(self, client):
        """Test token refresh flow."""
        # TODO: implement
        pass

    def test_logout(self, client, auth_headers):
        """Test logout invalidates tokens."""
        # TODO: implement
        pass

    def test_csrf_required_for_mutations(self, client, auth_headers):
        """Test CSRF token required for POST/PUT/DELETE."""
        # TODO: implement
        pass
