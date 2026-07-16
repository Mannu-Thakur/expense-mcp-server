from mcp.server.fastmcp import FastMCP

from app.config import settings

mcp = FastMCP(
    name=settings.MCP_SERVER_NAME,
    instructions="An MCP server for managing personal expenses.",
    host=settings.HOST,
    port=settings.PORT,
    streamable_http_path="/mcp",
)