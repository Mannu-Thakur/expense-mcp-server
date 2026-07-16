from app.mcp_instance import mcp
from app.services.expense_service import ExpenseService


@mcp.tool()
def top_merchants(limit: int = 5) -> list[dict]:
    """Show merchants with the highest total spending."""
    return ExpenseService.top_merchants(limit)