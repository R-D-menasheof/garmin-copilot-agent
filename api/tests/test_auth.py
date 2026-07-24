"""Tests for shared.auth — SSO/JWT (Entra External ID) + legacy api-key.

TDD RED phase: written before the SSO implementation.

Strategy: use a real RSA keypair to sign real JWTs and exercise PyJWT's
actual signature/issuer/audience/expiry validation. Only the JWKS *fetch*
(network) is mocked, via patching the module's ``_jwks_client`` factory.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

import shared.auth as auth_mod
from shared.auth import resolve_identity, resolve_user, verify_api_key

# ── Test signing key + config ─────────────────────────────────────

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_ISSUER = "https://vitalis.ciamlogin.com/tenant-abc/v2.0"
_AUDIENCE = "api://vitalis-client-id"


def _make_token(claims: dict | None = None, key=None) -> str:
    """Sign a JWT with sensible defaults; ``claims`` overrides any field."""
    now = int(time.time())
    payload = {
        "iss": _ISSUER,
        "aud": _AUDIENCE,
        "iat": now,
        "exp": now + 3600,
        "oid": "user-guid-123",
        **(claims or {}),
    }
    return jwt.encode(payload, key or _PRIVATE_KEY, algorithm="RS256")


def _req(headers: dict) -> MagicMock:
    req = MagicMock()
    req.headers = headers
    return req


@pytest.fixture(autouse=True)
def _auth_env(monkeypatch):
    monkeypatch.setenv("AUTH_JWKS_URL", "https://vitalis.ciamlogin.com/keys")
    monkeypatch.setenv("AUTH_ISSUER", _ISSUER)
    monkeypatch.setenv("AUTH_AUDIENCE", _AUDIENCE)
    monkeypatch.setenv("VITALIS_API_KEY", "legacy-owner-key")
    monkeypatch.setenv("VITALIS_OWNER_USER_ID", "roei")
    yield


@pytest.fixture
def mock_jwks():
    """Patch the JWKS client so signing-key lookup returns our public key."""
    signing_key = MagicMock()
    signing_key.key = _PRIVATE_KEY.public_key()
    client = MagicMock()
    client.get_signing_key_from_jwt.return_value = signing_key
    with patch.object(auth_mod, "_jwks_client", return_value=client):
        yield client


# ── JWT path ──────────────────────────────────────────────────────


class TestResolveJwt:
    def test_valid_token_returns_oid(self, mock_jwks) -> None:
        token = _make_token({"oid": "user-guid-123", "sub": "subj"})
        assert resolve_user(_req({"Authorization": f"Bearer {token}"})) == "user-guid-123"

    def test_falls_back_to_sub_when_no_oid(self, mock_jwks) -> None:
        token = _make_token({"oid": None, "sub": "subject-1"})
        assert resolve_user(_req({"Authorization": f"Bearer {token}"})) == "subject-1"

    def test_identity_exposes_name_and_email(self, mock_jwks) -> None:
        token = _make_token({"oid": "u1", "name": "Dana", "email": "d@x.com"})
        ident = resolve_identity(_req({"Authorization": f"Bearer {token}"}))
        assert ident is not None
        assert ident.user_id == "u1"
        assert ident.name == "Dana"
        assert ident.email == "d@x.com"
        assert ident.via == "jwt"

    def test_lowercase_authorization_header(self, mock_jwks) -> None:
        token = _make_token({"oid": "u2"})
        assert resolve_user(_req({"authorization": f"Bearer {token}"})) == "u2"

    def test_bad_signature_returns_none(self, mock_jwks) -> None:
        token = _make_token({"oid": "u1"}, key=_OTHER_KEY)
        assert resolve_user(_req({"Authorization": f"Bearer {token}"})) is None

    def test_wrong_audience_returns_none(self, mock_jwks) -> None:
        token = _make_token({"aud": "api://someone-else"})
        assert resolve_user(_req({"Authorization": f"Bearer {token}"})) is None

    def test_wrong_issuer_returns_none(self, mock_jwks) -> None:
        token = _make_token({"iss": "https://evil.example/v2.0"})
        assert resolve_user(_req({"Authorization": f"Bearer {token}"})) is None

    def test_expired_returns_none(self, mock_jwks) -> None:
        now = int(time.time())
        token = _make_token({"iat": now - 7200, "exp": now - 3600})
        assert resolve_user(_req({"Authorization": f"Bearer {token}"})) is None

    def test_malformed_token_returns_none(self, mock_jwks) -> None:
        assert resolve_user(_req({"Authorization": "Bearer not-a-jwt"})) is None

    def test_missing_header_returns_none(self, mock_jwks) -> None:
        assert resolve_user(_req({})) is None


# ── Legacy api-key path (transitional) ────────────────────────────


class TestLegacyApiKey:
    def test_valid_api_key_returns_owner(self, mock_jwks) -> None:
        assert resolve_user(_req({"x-api-key": "legacy-owner-key"})) == "roei"

    def test_identity_via_is_api_key(self, mock_jwks) -> None:
        ident = resolve_identity(_req({"x-api-key": "legacy-owner-key"}))
        assert ident is not None
        assert ident.user_id == "roei"
        assert ident.via == "api-key"

    def test_wrong_api_key_returns_none(self, mock_jwks) -> None:
        assert resolve_user(_req({"x-api-key": "nope"})) is None

    def test_jwt_takes_precedence_over_api_key(self, mock_jwks) -> None:
        token = _make_token({"oid": "jwt-user"})
        req = _req({"Authorization": f"Bearer {token}", "x-api-key": "legacy-owner-key"})
        assert resolve_user(req) == "jwt-user"

    def test_invalid_jwt_falls_back_to_api_key(self, mock_jwks) -> None:
        req = _req({"Authorization": "Bearer garbage", "x-api-key": "legacy-owner-key"})
        assert resolve_user(req) == "roei"


# ── verify_api_key (back-compat wrapper) ──────────────────────────


class TestVerifyApiKey:
    def test_true_for_valid_api_key(self, mock_jwks) -> None:
        assert verify_api_key(_req({"x-api-key": "legacy-owner-key"})) is True

    def test_true_for_valid_jwt(self, mock_jwks) -> None:
        token = _make_token({"oid": "u1"})
        assert verify_api_key(_req({"Authorization": f"Bearer {token}"})) is True

    def test_false_for_unauthenticated(self, mock_jwks) -> None:
        assert verify_api_key(_req({})) is False


# ── JWKS not configured (pre-Entra transitional deploy) ───────────


class TestJwksNotConfigured:
    def test_no_jwks_url_still_allows_api_key(self, monkeypatch) -> None:
        monkeypatch.delenv("AUTH_JWKS_URL", raising=False)
        auth_mod._jwks_client.cache_clear()
        assert resolve_user(_req({"x-api-key": "legacy-owner-key"})) == "roei"

    def test_no_jwks_url_rejects_bearer(self, monkeypatch) -> None:
        monkeypatch.delenv("AUTH_JWKS_URL", raising=False)
        auth_mod._jwks_client.cache_clear()
        token = _make_token({"oid": "u1"})
        assert resolve_user(_req({"Authorization": f"Bearer {token}"})) is None
