from pydantic import Field

from app.auth import get_request_owner_id
from app.mcp_instance import mcp
from app.services.expense_service import ExpenseService


@mcp.tool()
def top_merchants(limit: int = Field(default=5, ge=1, le=50)) -> list[dict]:
    """Show this user's highest-spend merchants, separated by currency."""
    return ExpenseService.top_merchants(limit, owner_id=get_request_owner_id())