from app.mcp_instance import mcp
from app.services.expense_service import ExpenseService


@mcp.tool()
def category_summary() -> list[dict]:
    """Get expense totals grouped by category."""
    return ExpenseService.category_summary()