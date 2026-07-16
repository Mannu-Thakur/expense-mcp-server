from app.mcp_instance import mcp
from app.services.expense_service import ExpenseService


@mcp.tool()
def search_expenses(query: str) -> list[dict]:
    """Search expenses by category, description, or merchant."""
    expenses = ExpenseService.search_expenses(query)
    return [
        {
            "id": e.id,
            "amount": e.amount,
            "category": e.category,
            "description": e.description,
            "merchant": e.merchant,
            "payment_method": e.payment_method,
            "currency": e.currency,
            "expense_date": str(e.expense_date),
        }
        for e in expenses
    ]