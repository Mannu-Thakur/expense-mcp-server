from app.auth import get_request_owner_id
from app.mcp_instance import mcp
from app.services.expense_service import ExpenseService


@mcp.tool()
def category_summary() -> list[dict]:
    """Show this user's all-time category totals, separated by currency."""
    return ExpenseService.category_summary(owner_id=get_request_owner_id())