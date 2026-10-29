"""Supabase JWT verification.

The frontend signs users in with Supabase Auth and sends the access token in the
`Authorization: Bearer <token>` header. The API never sees passwords: it only
verifies the token signature and reads the user id from the `sub` claim.

Two signing modes are supported:
- HS256 with the project's JWT secret (legacy Supabase projects);
- asymmetric keys (ES256 / RS256) fetched from the project's JWKS endpoint.
"""

from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None = None
    full_name: str | None = None


@lru_cache
def _jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_keys=True)


def decode_token(token: str, settings: Settings) -> dict:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise _unauthorized("Malformed token") from exc

    alg = header.get("alg", "")
    try:
        if alg == "HS256":
            if not settings.supabase_jwt_secret:
                raise _unauthorized("HS256 token received but SUPABASE_JWT_SECRET is not set")
            key = settings.supabase_jwt_secret
        elif alg in ("ES256", "RS256"):
            if not settings.supabase_url:
                raise _unauthorized("Asymmetric token received but SUPABASE_URL is not set")
            key = _jwks_client(settings.supabase_jwks_url).get_signing_key_from_jwt(token).key
        else:
            raise _unauthorized(f"Unsupported token algorithm: {alg or 'none'}")

        return jwt.decode(
            token,
            key,
            algorithms=[alg],
            audience=settings.supabase_jwt_audience,
            options={"require": ["sub", "exp"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("Token expired") from exc
    except jwt.PyJWTError as exc:
        raise _unauthorized("Invalid token") from exc


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    if creds is None or creds.scheme.lower() != "bearer":
        raise _unauthorized("Missing bearer token")

    payload = decode_token(creds.credentials, settings)
    metadata = payload.get("user_metadata") or {}
    return CurrentUser(
        id=payload["sub"],
        email=payload.get("email"),
        full_name=metadata.get("full_name") or metadata.get("name"),
    )


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
