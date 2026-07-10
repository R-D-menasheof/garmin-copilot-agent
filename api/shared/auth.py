"""Shared auth helper for API endpoints.

Two authentication paths, tried in order:

1. **SSO / JWT (Microsoft Entra External ID)** — validate an
   ``Authorization: Bearer <jwt>`` token against the tenant's JWKS
   (signature + issuer + audience + expiry) and derive the stable
   ``user_id`` from the ``oid`` (or ``sub``) claim.
2. **Legacy ``x-api-key``** — transitional owner access during the
   multi-user rollout. Maps the shared key to the owner's ``user_id``.

The resolved ``user_id`` is used to scope all Blob Storage access, so it
is ALWAYS derived server-side here and never taken from client input.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from functools import lru_cache

import jwt
from jwt import PyJWKClient

logger = logging.getLogger(__name__)


@dataclass
class Identity:
    """Authenticated caller identity."""

    user_id: str
    name: str = ""
    email: str = ""
    via: str = "jwt"  # "jwt" | "api-key"


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient | None:
    """Return a cached JWKS client, or None if SSO isn't configured yet."""
    url = os.environ.get("AUTH_JWKS_URL", "")
    if not url:
        return None
    return PyJWKClient(url)


def _resolve_jwt(token: str) -> Identity | None:
    """Validate a Bearer JWT and return the caller Identity, or None."""
    client = _jwks_client()
    if client is None:
        return None

    issuer = os.environ.get("AUTH_ISSUER", "")
    audience = os.environ.get("AUTH_AUDIENCE", "")
    try:
        signing_key = client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer or None,
            audience=audience or None,
            options={"require": ["exp"]},
        )
    except Exception as exc:  # noqa: BLE001 — any failure = unauthenticated
        logger.warning("JWT validation failed: %s", exc)
        return None

    # Entra External ID: ``oid`` is the stable per-user GUID; fall back to sub.
    user_id = claims.get("oid") or claims.get("sub")
    if not user_id:
        return None
    return Identity(
        user_id=str(user_id),
        name=str(claims.get("name", "")),
        email=str(claims.get("email") or claims.get("preferred_username", "")),
        via="jwt",
    )


def resolve_identity(req) -> Identity | None:
    """Resolve the authenticated caller from a request.

    Tries SSO JWT first, then the legacy shared api-key. Returns None when
    the request carries no valid credentials.

    Args:
        req: Azure Functions HttpRequest (or a mock with a ``.headers`` dict).
    """
    headers = req.headers
    auth_header = headers.get("Authorization", "") or headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        identity = _resolve_jwt(auth_header[len("Bearer "):].strip())
        if identity is not None:
            return identity

    expected = os.environ.get("VITALIS_API_KEY", "")
    actual = headers.get("x-api-key", "")
    if expected and actual == expected:
        owner_id = os.environ.get("VITALIS_OWNER_USER_ID", "roei")
        return Identity(user_id=owner_id, via="api-key")

    return None


def resolve_user(req) -> str | None:
    """Return the authenticated ``user_id``, or None if unauthenticated."""
    identity = resolve_identity(req)
    return identity.user_id if identity else None


def verify_api_key(req) -> bool:
    """Back-compat: True when the request is authenticated (any valid user).

    Retained for ingestion endpoints that don't touch per-user data.
    """
    return resolve_identity(req) is not None
