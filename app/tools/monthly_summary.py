from app.mcp_instance import mcp
from app.services.expense_service import ExpenseService


@mcp.tool()
def monthly_summary() -> dict:
    """Get a summary of the current month's expenses."""
    return ExpenseService.monthly_summary()