from app.auth import get_request_owner_id
from app.mcp_instance import mcp
from app.services.expense_service import ExpenseService


@mcp.tool()
def monthly_summary() -> dict:
    """Summarize this user's current UTC month, with totals separated by currency."""
    return ExpenseService.monthly_summary(owner_id=get_request_owner_id())