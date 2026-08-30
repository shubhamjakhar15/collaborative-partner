import time
import pytest
from unittest.mock import patch, MagicMock
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import jwt
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import (
    AuthenticatedUser,
    verify_clerk_token,
    verify_user_access,
    get_current_user,
    derive_jwks_url,
    is_dev_mock_enabled,
    jwks_cache,
)
from app.db.repository import reset_db_client
from tests.test_adaptation_lifecycle import InMemoryFirestoreClient


@pytest.fixture(autouse=True)
def setup_in_memory_db():
    mock_client = InMemoryFirestoreClient()
    reset_db_client(mock_client)
    yield
    reset_db_client(None)


@pytest.fixture
def client():
    return TestClient(app)


# -----------------------------------------------------------------------------
# RSA KEY FIXTURES FOR JWT SIMULATION
# -----------------------------------------------------------------------------
@pytest.fixture(scope="session")
def rsa_keys():
    """Generates an RSA key pair for testing JWT signatures."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()
    
    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pem_public = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return {"private": pem_private, "public": pem_public, "kid": "test_key_1"}


def create_test_jwt(rsa_keys, user_id="user_test_123", email="test@example.com", expires_in=3600, extra_claims=None):
    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": email,
        "sid": "sess_abc123",
        "iat": now,
        "nbf": now - 10,
        "exp": now + expires_in,
    }
    if extra_claims:
        payload.update(extra_claims)

    headers = {
        "kid": rsa_keys["kid"],
        "alg": "RS256"
    }
    return jwt.encode(payload, rsa_keys["private"], algorithm="RS256", headers=headers)


# -----------------------------------------------------------------------------
# 1. UNIT TESTS: TOKEN VERIFICATION
# -----------------------------------------------------------------------------
def test_verify_valid_clerk_token(rsa_keys):
    """Verify that a valid signed JWT is successfully decoded into AuthenticatedUser."""
    token = create_test_jwt(rsa_keys, user_id="user_2valid", email="alice@test.com")

    # Mock PyJWKClient to return public key for the token's kid
    mock_signing_key = MagicMock()
    mock_signing_key.key = rsa_keys["public"]

    with patch("jwt.PyJWKClient.get_signing_key_from_jwt", return_value=mock_signing_key):
        user = verify_clerk_token(token)
        assert isinstance(user, AuthenticatedUser)
        assert user.user_id == "user_2valid"
        assert user.email == "alice@test.com"
        assert user.session_id == "sess_abc123"


def test_verify_expired_token_raises_401(rsa_keys):
    """Verify that an expired JWT raises 401 Unauthorized."""
    expired_token = create_test_jwt(rsa_keys, user_id="user_expired", expires_in=-100)

    mock_signing_key = MagicMock()
    mock_signing_key.key = rsa_keys["public"]

    with patch("jwt.PyJWKClient.get_signing_key_from_jwt", return_value=mock_signing_key):
        with pytest.raises(HTTPException) as exc_info:
            verify_clerk_token(expired_token)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()


def test_verify_invalid_token_raises_401():
    """Verify that a garbled string raises 401 Unauthorized."""
    with pytest.raises(HTTPException) as exc_info:
        verify_clerk_token("not.a.valid.jwt.token")
    assert exc_info.value.status_code == 401


# -----------------------------------------------------------------------------
# 2. UNIT TESTS: TENANT ISOLATION & ACCESS CONTROL
# -----------------------------------------------------------------------------
def test_verify_user_access_matching_user():
    """Accessing own resource succeeds."""
    current_user = AuthenticatedUser(user_id="user_123")
    result = verify_user_access("user_123", current_user)
    assert result == "user_123"


def test_verify_user_access_me_alias():
    """'me' alias resolves to authenticated user's ID."""
    current_user = AuthenticatedUser(user_id="user_123")
    result = verify_user_access("me", current_user)
    assert result == "user_123"


def test_verify_user_access_mismatched_user_raises_403():
    """Accessing another user's resource raises 403 Forbidden."""
    current_user = AuthenticatedUser(user_id="user_alice")
    with pytest.raises(HTTPException) as exc_info:
        verify_user_access("user_bob", current_user)
    assert exc_info.value.status_code == 403
    assert "access denied" in exc_info.value.detail.lower()


# -----------------------------------------------------------------------------
# 3. ENDPOINT INTEGRATION TESTS
# -----------------------------------------------------------------------------
def test_auth_me_endpoint_with_valid_token(client: TestClient, rsa_keys):
    """GET /auth/me returns the verified user identity."""
    token = create_test_jwt(rsa_keys, user_id="user_me_test", email="me@clerk.dev")

    mock_signing_key = MagicMock()
    mock_signing_key.key = rsa_keys["public"]

    with patch("jwt.PyJWKClient.get_signing_key_from_jwt", return_value=mock_signing_key):
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["user_id"] == "user_me_test"
        assert data["email"] == "me@clerk.dev"


def test_protected_routes_require_auth_when_dev_mock_disabled(client: TestClient):
    """When dev mock is disabled, requests without Bearer token return 401."""
    with patch("app.core.auth.is_dev_mock_enabled", return_value=False):
        res = client.get("/users/some_user/preferences")
        assert res.status_code == 401
        assert "authentication required" in res.json()["message"].lower()


def test_user_cannot_access_other_user_projects(client: TestClient, rsa_keys):
    """User Alice cannot read projects of User Bob (returns 403 Forbidden)."""
    token_alice = create_test_jwt(rsa_keys, user_id="user_alice")

    mock_signing_key = MagicMock()
    mock_signing_key.key = rsa_keys["public"]

    with patch("jwt.PyJWKClient.get_signing_key_from_jwt", return_value=mock_signing_key):
        response = client.get(
            "/users/user_bob/projects",
            headers={"Authorization": f"Bearer {token_alice}"}
        )
        assert response.status_code == 403
        assert "access denied" in response.json()["message"].lower()


def test_user_can_access_own_projects_using_me(client: TestClient, rsa_keys):
    """User can query /users/me/projects seamlessly."""
    token_alice = create_test_jwt(rsa_keys, user_id="user_alice")

    mock_signing_key = MagicMock()
    mock_signing_key.key = rsa_keys["public"]

    with patch("jwt.PyJWKClient.get_signing_key_from_jwt", return_value=mock_signing_key):
        response = client.get(
            "/users/me/projects",
            headers={"Authorization": f"Bearer {token_alice}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["user_id"] == "user_alice"
