"""Tests for internal JWT authentication"""

import pytest
import jwt
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.auth import verify_internal_token


# Generate test RSA key pair for testing
@pytest.fixture
def test_rsa_keypair():
    """Generate a test RSA key pair"""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    return private_key


@pytest.fixture
def test_public_key_pem(test_rsa_keypair):
    """Get PEM encoded public key"""
    public_key = test_rsa_keypair.public_key()
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return pem.decode()


@pytest.fixture
def test_private_key_pem(test_rsa_keypair):
    """Get PEM encoded private key"""
    pem = test_rsa_keypair.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    return pem.decode()


@pytest.fixture
def valid_token(test_private_key_pem):
    """Create a valid JWT token"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "node-gateway",
        "aud": "python-ai-service",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "jti": "test-uuid-123"
    }

    token = jwt.encode(
        payload,
        test_private_key_pem,
        algorithm="RS256"
    )
    return token


@pytest.fixture
def expired_token(test_private_key_pem):
    """Create an expired JWT token"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "node-gateway",
        "aud": "python-ai-service",
        "iat": now - timedelta(hours=1),
        "exp": now - timedelta(minutes=30),
        "jti": "test-uuid-expired"
    }

    token = jwt.encode(
        payload,
        test_private_key_pem,
        algorithm="RS256"
    )
    return token


@pytest.fixture
def wrong_audience_token(test_private_key_pem):
    """Create a token with wrong audience"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "node-gateway",
        "aud": "wrong-audience",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "jti": "test-uuid-wrong"
    }

    token = jwt.encode(
        payload,
        test_private_key_pem,
        algorithm="RS256"
    )
    return token


class TestVerifyInternalToken:
    """Tests for verify_internal_token function"""

    def test_valid_token_verification(self, valid_token, test_public_key_pem, monkeypatch):
        """Test that valid token is verified successfully"""
        # Mock settings
        import app.core.auth
        monkeypatch.setattr(
            app.core.auth.settings,
            "JWT_INTERNAL_PUBLIC_KEY",
            test_public_key_pem
        )

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=valid_token
        )

        result = verify_internal_token(credentials)

        assert result["sub"] == "node-gateway"
        assert result["aud"] == "python-ai-service"
        assert "exp" in result
        assert "iat" in result
        assert result["jti"] == "test-uuid-123"

    def test_expired_token_rejected(self, expired_token, test_public_key_pem, monkeypatch):
        """Test that expired token is rejected"""
        import app.core.auth
        monkeypatch.setattr(
            app.core.auth.settings,
            "JWT_INTERNAL_PUBLIC_KEY",
            test_public_key_pem
        )

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=expired_token
        )

        with pytest.raises(HTTPException) as exc_info:
            verify_internal_token(credentials)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_wrong_audience_rejected(self, wrong_audience_token, test_public_key_pem, monkeypatch):
        """Test that token with wrong audience is rejected"""
        import app.core.auth
        monkeypatch.setattr(
            app.core.auth.settings,
            "JWT_INTERNAL_PUBLIC_KEY",
            test_public_key_pem
        )

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=wrong_audience_token
        )

        with pytest.raises(HTTPException) as exc_info:
            verify_internal_token(credentials)

        assert exc_info.value.status_code == 401
        assert "audience" in exc_info.value.detail.lower() or "Invalid" in exc_info.value.detail

    def test_invalid_token_rejected(self, test_public_key_pem, monkeypatch):
        """Test that invalid token is rejected"""
        import app.core.auth
        monkeypatch.setattr(
            app.core.auth.settings,
            "JWT_INTERNAL_PUBLIC_KEY",
            test_public_key_pem
        )

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.token.here"
        )

        with pytest.raises(HTTPException) as exc_info:
            verify_internal_token(credentials)

        assert exc_info.value.status_code == 401

    def test_missing_public_key_raises_error(self, valid_token, monkeypatch):
        """Test that missing public key configuration raises error"""
        import app.core.auth
        monkeypatch.setattr(
            app.core.auth.settings,
            "JWT_INTERNAL_PUBLIC_KEY",
            ""
        )

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=valid_token
        )

        with pytest.raises(HTTPException) as exc_info:
            verify_internal_token(credentials)

        assert exc_info.value.status_code == 401
        assert "not configured" in exc_info.value.detail.lower()

    def test_token_without_required_claims_rejected(self, test_private_key_pem, test_public_key_pem, monkeypatch):
        """Test that token missing required claims is rejected"""
        import app.core.auth
        monkeypatch.setattr(
            app.core.auth.settings,
            "JWT_INTERNAL_PUBLIC_KEY",
            test_public_key_pem
        )

        # Token without 'sub' claim
        now = datetime.now(timezone.utc)
        payload = {
            "aud": "python-ai-service",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "jti": "test-uuid"
        }

        token = jwt.encode(payload, test_private_key_pem, algorithm="RS256")

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )

        with pytest.raises(HTTPException) as exc_info:
            verify_internal_token(credentials)

        assert exc_info.value.status_code == 401
