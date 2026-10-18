from typing import Literal

from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp.server.auth.routes import create_protected_resource_routes
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

from app.auth import JwtTokenVerifier
from app.config import settings
from app.database import db
from app.logging_config import get_logger

logger = get_logger(__name__)


class SecureFastMCP(FastMCP):
    def streamable_http_app(self) -> Starlette:
        app = super().streamable_http_app()
        auth = self.settings.auth
        if auth is None or auth.resource_server_url is None:
            return app

        metadata_route = create_protected_resource_routes(
            resource_url=auth.resource_server_url,
            authorization_servers=[auth.issuer_url],
            scopes_supported=["expenses:read", "expenses:write"],
        )[0]
        for index, route in enumerate(app.routes):
            if getattr(route, "path", None) == metadata_route.path:
                app.routes[index] = metadata_route
                break
        else:
            raise RuntimeError("Unable to register OAuth metadata for both expense scopes.")
        return app

    def run(
        self,
        transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
        mount_path: str | None = None,
    ) -> None:
        if transport == "sse":
            raise RuntimeError("SSE transport is disabled. Use authenticated Streamable HTTP instead.")
        if transport == "streamable-http" and (
            self.settings.auth is None or self._token_verifier is None
        ):
            raise RuntimeError("HTTP transport is disabled until OAuth authentication is configured.")
        super().run(transport=transport, mount_path=mount_path)


_oauth = settings.oauth_config(required=settings.TRANSPORT.lower() == "streamable-http")
_auth_settings = None
_token_verifier = None
if _oauth:
    _token_verifier = JwtTokenVerifier(
        jwks_url=_oauth["jwks_url"],
        issuer_url=_oauth["issuer_url"],
        audience=_oauth["audience"],
        resource_url=_oauth["resource_url"],
        algorithm=_oauth["algorithm"],
    )
    _auth_settings = AuthSettings(
        issuer_url=AnyHttpUrl(_oauth["issuer_url"]),
        resource_server_url=AnyHttpUrl(_oauth["resource_url"]),
        required_scopes=["expenses:read"],
    )

mcp = SecureFastMCP(
    name=settings.MCP_SERVER_NAME,
    instructions="A personal expense ledger. Reads require expenses:read; changes require expenses:write.",
    host=settings.HOST,
    port=settings.PORT,
    streamable_http_path="/mcp",
    auth=_auth_settings,
    token_verifier=_token_verifier,
)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Public infrastructure check with database readiness status."""
    try:
        with db.engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        return JSONResponse({"status": "ok"})
    except Exception as exc:
        logger.warning("Health check database probe failed (%s).", type(exc).__name__)
        return JSONResponse({"status": "unavailable"}, status_code=503)
