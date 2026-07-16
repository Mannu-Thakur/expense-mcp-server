from app.mcp_instance import mcp
from app.services.expense_service import ExpenseService


@mcp.tool()
def delete_expense(expense_id: int) -> dict:
    """Delete an expense by ID."""
    return ExpenseService.delete_expense(expense_id)