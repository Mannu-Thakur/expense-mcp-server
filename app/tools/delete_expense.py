from app.auth import get_request_owner_id, require_write_scope
from app.mcp_instance import mcp
from app.services.expense_service import ExpenseService


@mcp.tool()
def delete_expense(expense_id: int) -> dict:
    """Delete one of this user's expenses. HTTP callers need expenses:write."""
    require_write_scope()
    return ExpenseService.delete_expense(expense_id, owner_id=get_request_owner_id())