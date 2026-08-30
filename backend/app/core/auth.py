import base64
import json
import logging
import os
import time
from typing import Any, Optional
import jwt
from jwt import PyJWKClient
from pydantic import BaseModel, Field
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger("project_partner.auth")

# -----------------------------------------------------------------------------
# AUTHENTICATION DATA MODELS
# -----------------------------------------------------------------------------
class AuthenticatedUser(BaseModel):
    """Represents a verified Clerk user identity extracted from session token."""
    user_id: str = Field(..., description="Clerk user ID (sub claim, e.g. 'user_2xxx')")
    session_id: Optional[str] = Field(default=None, description="Clerk session ID (sid claim)")
    email: Optional[str] = Field(default=None, description="User email address if present in claims")
    claims: dict[str, Any] = Field(default_factory=dict, description="Complete raw JWT claims payload")


# -----------------------------------------------------------------------------
# CLERK CONFIGURATION & JWKS RESOLVER
# -----------------------------------------------------------------------------
def get_clerk_secret_key() -> Optional[str]:
    return os.getenv("CLERK_SECRET_KEY", "").strip() or None


def get_clerk_publishable_key() -> Optional[str]:
    return os.getenv("CLERK_PUBLISHABLE_KEY", "").strip() or None


def is_dev_mock_enabled() -> bool:
    """
    Returns True if dev mock mode is active:
    - If explicitly set via CLERK_ENABLE_DEV_MOCK=True, OR
    - If neither CLERK_SECRET_KEY nor CLERK_PUBLISHABLE_KEY is configured.
    """
    explicit = os.getenv("CLERK_ENABLE_DEV_MOCK", "").strip().lower()
    if explicit in ("true", "1", "yes"):
        return True
    if explicit in ("false", "0", "no"):
        return False
    # If no keys are provided, default to dev mock mode for seamless local setup
    return not (get_clerk_secret_key() or get_clerk_publishable_key())


def derive_jwks_url() -> Optional[str]:
    """
    Resolves the JWKS URL to verify Clerk JWTs:
    1. Explicit CLERK_JWKS_URL env var if set.
    2. Derived from CLERK_PUBLISHABLE_KEY base64 frontend API domain.
    3. Fallback to https://api.clerk.com/v1/jwks (requires secret key in request).
    """
    explicit_jwks = os.getenv("CLERK_JWKS_URL", "").strip()
    if explicit_jwks:
        return explicit_jwks

    pk = get_clerk_publishable_key()
    if pk and (pk.startswith("pk_test_") or pk.startswith("pk_live_")):
        try:
            # Clerk publishable key format: pk_test_<base64_domain>$
            encoded_part = pk.split("_", 2)[2]
            # Add padding if needed
            padding = 4 - (len(encoded_part) % 4)
            if padding != 4:
                encoded_part += "=" * padding
            decoded_domain = base64.b64decode(encoded_part).decode("utf-8").rstrip("$")
            if decoded_domain:
                return f"https://{decoded_domain}/.well-known/jwks.json"
        except Exception as e:
            logger.warning(f"Failed to decode CLERK_PUBLISHABLE_KEY for JWKS URL: {e}")

    return "https://api.clerk.com/v1/jwks"


# -----------------------------------------------------------------------------
# JWKS CACHE & VERIFICATION ENGINE
# -----------------------------------------------------------------------------
class ClerkJWKSCache:
    """Thread-safe cache for Clerk JWKS keys with automatic TTL refresh."""
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._jwk_client: Optional[PyJWKClient] = None
        self._last_jwks_url: Optional[str] = None

    def get_jwk_client(self, jwks_url: str) -> PyJWKClient:
        if self._jwk_client is None or self._last_jwks_url != jwks_url:
            secret_key = get_clerk_secret_key()
            headers = {}
            if secret_key and "api.clerk.com" in jwks_url:
                headers["Authorization"] = f"Bearer {secret_key}"
            
            self._jwk_client = PyJWKClient(
                jwks_url,
                cache_keys=True,
                max_cached_keys=16,
                headers=headers if headers else None,
                lifespan=self.ttl_seconds
            )
            self._last_jwks_url = jwks_url
        return self._jwk_client

    def reset(self):
        self._jwk_client = None
        self._last_jwks_url = None


jwks_cache = ClerkJWKSCache()


def get_authorized_parties() -> list[str]:
    """Returns configured allowed authorized parties (azp) for CSRF/origin safety."""
    azp_str = os.getenv("CLERK_AUTHORIZED_PARTIES", "").strip()
    if not azp_str:
        return []
    return [p.strip() for p in azp_str.split(",") if p.strip()]


def verify_clerk_token(token: str) -> AuthenticatedUser:
    """
    Validates a Clerk JWT session token using JWKS.
    Extracts user_id, session_id, email, and raw claims.
    """
    if not token or not isinstance(token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or empty authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jwks_url = derive_jwks_url()
    try:
        jwk_client = jwks_cache.get_jwk_client(jwks_url)
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        
        # Verify and decode JWT claims
        decoded_claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "EdDSA", "ES256"],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "require": ["sub", "exp"],
            }
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired. Please refresh your session.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Clerk token validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected error during Clerk JWKS verification: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to authenticate token with Clerk identity provider.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Optional: Verify authorized party (azp)
    authorized_parties = get_authorized_parties()
    token_azp = decoded_claims.get("azp")
    if authorized_parties and token_azp and token_azp not in authorized_parties:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorized party '{token_azp}' is not permitted.",
        )

    user_id = decoded_claims.get("sub")
    session_id = decoded_claims.get("sid")
    email = decoded_claims.get("email") or decoded_claims.get("primary_email_address")

    return AuthenticatedUser(
        user_id=user_id,
        session_id=session_id,
        email=email,
        claims=decoded_claims,
    )


# -----------------------------------------------------------------------------
# FASTAPI SECURITY DEPENDENCIES
# -----------------------------------------------------------------------------
security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> AuthenticatedUser:
    """
    FastAPI dependency for protected routes.
    Extracts Bearer token from 'Authorization' header and verifies it.
    
    If in dev mock mode and no token is provided, returns a default mock user.
    """
    if credentials and credentials.credentials:
        return verify_clerk_token(credentials.credentials)

    # Fallback to dev mock mode if enabled
    if is_dev_mock_enabled():
        # Check if client passed a custom user_id in headers or query for dev testing
        dev_user_id = request.headers.get("X-Dev-User-Id", "demo-user")
        return AuthenticatedUser(
            user_id=dev_user_id,
            session_id="dev-mock-session",
            email="demo@projectpartner.local",
            claims={"sub": dev_user_id, "dev_mock": True},
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please provide a valid Bearer token in Authorization header.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Optional[AuthenticatedUser]:
    """
    FastAPI dependency for optionally authenticated routes.
    Returns AuthenticatedUser if valid token is passed, else None.
    """
    if credentials and credentials.credentials:
        try:
            return verify_clerk_token(credentials.credentials)
        except HTTPException:
            return None
    return None


def verify_user_access(user_id: str, current_user: AuthenticatedUser) -> str:
    """
    Enforces tenant isolation and access control:
    - Resolves alias 'me' to the authenticated user ID.
    - Ensures user_id matches the authenticated user ID.
    - Raises 403 Forbidden if mismatched.
    Returns the resolved user_id.
    """
    if user_id.lower() == "me":
        return current_user.user_id

    if user_id != current_user.user_id:
        logger.warning(
            f"Access denied: Authenticated user '{current_user.user_id}' attempted to access resources of user '{user_id}'."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: You do not have permission to access resources for user '{user_id}'.",
        )

    return user_id
