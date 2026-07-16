from app.mcp_instance import mcp
from app.services.expense_service import ExpenseService


@mcp.tool()
def list_expenses() -> list[dict]:
    """List all expenses sorted by date descending."""
    expenses = ExpenseService.list_expenses()
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