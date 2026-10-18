import asyncio
import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import ValidationError

import app.auth as auth
from app.config import Settings


ISSUER = "https://identity.example.test/"
AUDIENCE = "https://expenses.example.test/mcp"
RESOURCE = "https://expenses.example.test/mcp"


@pytest.fixture
def key_pair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def make_token(private_key, **overrides):
    claims = {
        "iss": ISSUER,
        "sub": "user-123",
        "aud": AUDIENCE,
        "exp": int(time.time()) + 300,
        "scope": "expenses:read expenses:write",
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key"})


def make_verifier(monkeypatch, public_key):
    verifier = auth.JwtTokenVerifier(
        jwks_url=f"{ISSUER}.well-known/jwks.json",
        issuer_url=ISSUER,
        audience=AUDIENCE,
        resource_url=RESOURCE,
    )
    monkeypatch.setattr(
        verifier._jwks_client,
        "get_signing_key_from_jwt",
        lambda token: SimpleNamespace(key=public_key),
    )
    return verifier


def test_jwt_verifier_accepts_valid_token_and_maps_identity(monkeypatch, key_pair):
    private_key, public_key = key_pair
    verifier = make_verifier(monkeypatch, public_key)

    access_token = asyncio.run(verifier.verify_token(make_token(private_key)))

    assert access_token is not None
    assert access_token.subject == "user-123"
    assert access_token.client_id == "user-123"
    assert access_token.scopes == ["expenses:read", "expenses:write"]
    assert access_token.resource == RESOURCE
    assert access_token.claims == {"iss": ISSUER}


@pytest.mark.parametrize(
    "claims",
    [
        {"aud": "https://other.example.test/mcp"},
        {"iss": "https://other-issuer.example.test/"},
        {"exp": int(time.time()) - 120},
        {"sub": "   "},
        {"scope": {"expenses:read": True}},
    ],
)
def test_jwt_verifier_rejects_invalid_or_malformed_claims(monkeypatch, key_pair, claims):
    private_key, public_key = key_pair
    verifier = make_verifier(monkeypatch, public_key)

    assert asyncio.run(verifier.verify_token(make_token(private_key, **claims))) is None


def test_jwt_verifier_rejects_symmetric_algorithm(monkeypatch, key_pair):
    _, public_key = key_pair
    verifier = make_verifier(monkeypatch, public_key)
    token = jwt.encode(
        {
            "iss": ISSUER,
            "sub": "user-123",
            "aud": AUDIENCE,
            "exp": int(time.time()) + 300,
            "scope": "expenses:read",
        },
        "a-shared-secret-with-at-least-32-bytes",
        algorithm="HS256",
    )

    assert asyncio.run(verifier.verify_token(token)) is None


def test_owner_id_is_stable_and_separates_issuer_and_subject(monkeypatch):
    monkeypatch.setattr(auth.settings, "TRANSPORT", "streamable-http")
    token = SimpleNamespace(subject="user-123", claims={"iss": ISSUER})
    monkeypatch.setattr(auth, "get_access_token", lambda: token)
    first = auth.get_request_owner_id()
    assert auth.get_request_owner_id() == first

    token.claims = {"iss": "https://other-issuer.example.test/"}
    assert auth.get_request_owner_id() != first
    token.claims = {"iss": ISSUER}
    token.subject = "user-456"
    assert auth.get_request_owner_id() != first


def test_http_identity_and_write_scope_fail_closed(monkeypatch):
    monkeypatch.setattr(auth.settings, "TRANSPORT", "streamable-http")
    monkeypatch.setattr(auth, "get_access_token", lambda: None)
    with pytest.raises(PermissionError):
        auth.get_request_owner_id()
    with pytest.raises(PermissionError):
        auth.require_write_scope()

    token = SimpleNamespace(subject="user-123", claims={"iss": ISSUER}, scopes=["expenses:read"])
    monkeypatch.setattr(auth, "get_access_token", lambda: token)
    with pytest.raises(PermissionError, match="expenses:write"):
        auth.require_write_scope()

    token.scopes.append("expenses:write")
    auth.require_write_scope()


def test_every_mutating_tool_checks_write_scope_before_database_access(monkeypatch):
    from app.tools.add_expense import add_expense
    from app.tools.delete_expense import delete_expense
    from app.tools.update_expense import update_expense

    monkeypatch.setattr(auth.settings, "TRANSPORT", "streamable-http")
    monkeypatch.setattr(
        auth,
        "get_access_token",
        lambda: SimpleNamespace(scopes=["expenses:read"]),
    )

    with pytest.raises(PermissionError, match="expenses:write"):
        add_expense(amount=1, category="Food")
    with pytest.raises(PermissionError, match="expenses:write"):
        update_expense(expense_id=1, category="Food")
    with pytest.raises(PermissionError, match="expenses:write"):
        delete_expense(expense_id=1)


def test_local_stdio_uses_single_process_owner_and_allows_local_writes(monkeypatch):
    monkeypatch.setattr(auth.settings, "TRANSPORT", "stdio")
    monkeypatch.setattr(auth, "get_access_token", lambda: None)

    assert auth.get_request_owner_id() == auth.LOCAL_OWNER_ID
    auth.require_write_scope()


def test_oauth_configuration_requires_complete_https_resource_settings():
    with pytest.raises(ValueError, match="requires OAUTH"):
        Settings(_env_file=None, APP_ENV="production", TRANSPORT="streamable-http").oauth_config(
            required=True
        )

    configured = Settings(
        _env_file=None,
        APP_ENV="production",
        TRANSPORT="streamable-http",
        OAUTH_ISSUER_URL=ISSUER,
        OAUTH_JWKS_URL=f"{ISSUER}.well-known/jwks.json",
        OAUTH_AUDIENCE=AUDIENCE,
        OAUTH_RESOURCE_URL=RESOURCE,
        OAUTH_JWT_ALGORITHM="rs256",
    ).oauth_config(required=True)
    assert configured["algorithm"] == "RS256"
    assert configured["resource_url"] == RESOURCE


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"OAUTH_JWKS_URL": "http://identity.example.test/jwks"}, "HTTPS"),
        ({"OAUTH_RESOURCE_URL": "https://expenses.example.test/other"}, "ending in /mcp"),
        ({"OAUTH_RESOURCE_URL": "https://expenses.example.test/mcp/"}, "ending in /mcp"),
        ({"OAUTH_ISSUER_URL": "https://identity.example.test:70000/"}, "valid port"),
        ({"OAUTH_JWT_ALGORITHM": "HS256"}, "asymmetric"),
    ],
)
def test_oauth_configuration_rejects_insecure_or_invalid_values(overrides, message):
    values = {
        "APP_ENV": "production",
        "TRANSPORT": "streamable-http",
        "OAUTH_ISSUER_URL": ISSUER,
        "OAUTH_JWKS_URL": f"{ISSUER}.well-known/jwks.json",
        "OAUTH_AUDIENCE": AUDIENCE,
        "OAUTH_RESOURCE_URL": RESOURCE,
        "OAUTH_JWT_ALGORITHM": "RS256",
    }
    values.update(overrides)
    configured = Settings(_env_file=None, **values)

    with pytest.raises(ValueError, match=message):
        configured.oauth_config(required=True)


def test_settings_reject_invalid_settings_types():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, PORT="not-a-port")
