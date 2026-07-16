from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp.server.fastmcp import FastMCP

from app.config import settings

mcp = FastMCP(
    name=settings.MCP_SERVER_NAME,
    instructions="An MCP server for managing personal expenses.",
    host=settings.HOST,
    port=settings.PORT,
    streamable_http_path="/mcp",
)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for Render and other load balancers."""
    return JSONResponse({"status": "ok"})