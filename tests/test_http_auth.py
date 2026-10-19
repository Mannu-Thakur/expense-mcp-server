from starlette.requests import Request
from starlette.responses import JSONResponse
import asyncio

import httpx

from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

from app.mcp_instance import SecureMCPServer


ISSUER = AnyHttpUrl("https://identity.example.test/")
RESOURCE = AnyHttpUrl("https://expenses.example.test/mcp")


class StubTokenVerifier:
    async def verify_token(self, token: str) -> AccessToken | None:
        scopes_by_token = {
            "read": ["expenses:read"],
            "write-only": ["expenses:write"],
            "read-write": ["expenses:read", "expenses:write"],
        }
        scopes = scopes_by_token.get(token)
        if scopes is None:
            return None
        return AccessToken(
            token=token,
            client_id="test-client",
            scopes=scopes,
            expires_at=None,
            resource=str(RESOURCE),
            subject="test-user",
            claims={"iss": str(ISSUER)},
        )


def make_http_app():
    server = SecureMCPServer(
        name="test-expenses",
        auth=AuthSettings(
            issuer_url=ISSUER,
            resource_server_url=RESOURCE,
            required_scopes=["expenses:read"],
            validate_token_resource=True,
        ),
        token_verifier=StubTokenVerifier(),
    )

    @server.custom_route("/health", methods=["GET"])
    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return server.streamable_http_app(
        host="0.0.0.0",
        streamable_http_path="/mcp",
    )


def test_http_endpoint_requires_valid_read_scope_and_health_is_public():
    async def check():
        app = make_http_app()
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                assert (await client.get("/health")).status_code == 200
                assert (await client.get("/mcp")).status_code == 401

                legacy_initialize = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {"name": "auth-check", "version": "1"},
                    },
                }
                assert (
                    await client.post(
                        "/mcp",
                        json=legacy_initialize,
                        headers={"accept": "application/json, text/event-stream"},
                    )
                ).status_code == 401

                authenticated_initialize = await client.post(
                    "/mcp",
                    json=legacy_initialize,
                    headers={
                        "accept": "application/json, text/event-stream",
                        "authorization": "Bearer read",
                    },
                )
                assert authenticated_initialize.status_code == 200
                assert authenticated_initialize.headers.get("mcp-session-id")

                modern_discovery = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "server/discover",
                    "params": {
                        "protocolVersion": "2026-07-28",
                        "clientCapabilities": {},
                        "clientInfo": {"name": "auth-check", "version": "1"},
                    },
                }
                assert (
                    await client.post(
                        "/mcp",
                        json=modern_discovery,
                        headers={"accept": "application/json, text/event-stream"},
                    )
                ).status_code == 401
                assert (
                    await client.get(
                        "/mcp",
                        headers={"Authorization": "Bearer invalid"},
                    )
                ).status_code == 401
                assert (
                    await client.get(
                        "/mcp",
                        headers={"Authorization": "Bearer write-only"},
                    )
                ).status_code == 403
                # A valid read token reaches the MCP handler (GET is rejected by the
                # Streamable HTTP protocol handler, rather than by auth middleware).
                assert (
                    await client.get(
                        "/mcp",
                        headers={"Authorization": "Bearer read"},
                    )
                ).status_code not in {401, 403}

    asyncio.run(check())


def test_resource_metadata_advertises_read_and_write_scopes():
    async def check():
        app = make_http_app()
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                return await client.get("/.well-known/oauth-protected-resource/mcp")

    response = asyncio.run(check())
    assert response.status_code == 200
    assert response.json()["scopes_supported"] == ["expenses:read", "expenses:write"]


def test_http_without_oauth_is_healthy_but_mcp_is_disabled():
    server = SecureMCPServer(name="test-expenses")

    @server.custom_route("/health", methods=["GET"])
    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    app = server.streamable_http_app(host="0.0.0.0", streamable_http_path="/mcp")

    async def check():
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                assert (await client.get("/health")).status_code == 200
                assert (await client.get("/mcp")).status_code == 503
                response = await client.post(
                    "/mcp",
                    json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                    headers={"accept": "application/json, text/event-stream"},
                )
                assert response.status_code == 503
                assert response.json()["error"] == "oauth_not_configured"

    asyncio.run(check())


def test_sse_transport_is_disabled():
    server = SecureMCPServer(name="test-expenses")
    try:
        server.run(transport="sse")
    except RuntimeError as exc:
        assert "SSE transport is disabled" in str(exc)
    else:
        raise AssertionError("SSE should not start")
