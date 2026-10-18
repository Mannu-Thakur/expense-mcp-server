import asyncio
import hashlib

import jwt
from jwt import PyJWKClient
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier

from app.config import settings

LOCAL_OWNER_ID = "local"
WRITE_SCOPE = "expenses:write"


class JwtTokenVerifier(TokenVerifier):
    """Verify asymmetric JWT access tokens using the configured issuer JWKS."""

    def __init__(
        self,
        jwks_url: str,
        issuer_url: str,
        audience: str,
        resource_url: str,
        algorithm: str = "RS256",
    ) -> None:
        self._issuer_url = issuer_url
        self._audience = audience
        self._resource_url = resource_url
        self._algorithm = algorithm.upper()
        self._jwks_client = PyJWKClient(
            jwks_url,
            cache_jwk_set=True,
            lifespan=300,
            timeout=5,
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            signing_key = await asyncio.to_thread(
                self._jwks_client.get_signing_key_from_jwt,
                token,
            )
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=[self._algorithm],
                audience=self._audience,
                issuer=self._issuer_url,
                leeway=30,
                options={"require": ["exp", "iss", "sub", "aud"]},
            )
        except Exception:
            # Never log the bearer token or verifier exception text.
            return None

        subject = claims.get("sub")
        issuer = claims.get("iss")
        if not isinstance(subject, str) or not subject.strip():
            return None
        if not isinstance(issuer, str) or not issuer:
            return None

        raw_scopes = claims.get("scope", claims.get("scp", []))
        if isinstance(raw_scopes, str):
            scopes = raw_scopes.split()
        elif isinstance(raw_scopes, list) and all(isinstance(scope, str) for scope in raw_scopes):
            scopes = raw_scopes
        else:
            return None

        client_id = claims.get("client_id") or claims.get("azp") or subject
        if not isinstance(client_id, str) or not client_id:
            return None

        return AccessToken(
            token=token,
            client_id=client_id,
            scopes=scopes,
            expires_at=int(claims["exp"]),
            resource=self._resource_url,
            subject=subject,
            claims={"iss": issuer},
        )


def get_request_owner_id() -> str:
    """Return a stable owner key from the local process or verified HTTP identity."""
    access_token = get_access_token()
    if access_token is None:
        if settings.TRANSPORT.lower() == "stdio":
            return LOCAL_OWNER_ID
        raise PermissionError("An authenticated user identity is required.")

    subject = access_token.subject
    issuer = (access_token.claims or {}).get("iss")
    if not isinstance(subject, str) or not subject.strip():
        raise PermissionError("The verified token does not identify its subject.")
    if not isinstance(issuer, str) or not issuer:
        raise PermissionError("The verified token does not identify its issuer.")

    identity = f"{issuer}\0{subject}".encode("utf-8")
    return hashlib.sha256(identity).hexdigest()


def require_write_scope() -> None:
    """Require the write scope for HTTP mutations; local STDIO is process-scoped."""
    access_token = get_access_token()
    if access_token is None:
        if settings.TRANSPORT.lower() == "stdio":
            return
        raise PermissionError("An authenticated user identity is required.")

    if WRITE_SCOPE not in access_token.scopes:
        raise PermissionError("This operation requires the expenses:write scope.")
