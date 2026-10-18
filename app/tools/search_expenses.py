from pydantic import Field

from app.auth import get_request_owner_id
from app.mcp_instance import mcp
from app.services.expense_service import ExpenseService


@mcp.tool()
def search_expenses(query: str = Field(min_length=1, max_length=200)) -> list[dict]:
    """Search this user's expenses by category, description, or merchant."""
    expenses = ExpenseService.search_expenses(query, owner_id=get_request_owner_id())
    return [
        {
            "id": expense.id,
            "amount": float(expense.amount),
            "category": expense.category,
            "description": expense.description,
            "merchant": expense.merchant,
            "payment_method": expense.payment_method,
            "currency": expense.currency,
            "expense_date": str(expense.expense_date),
        }
        for expense in expenses
    ]