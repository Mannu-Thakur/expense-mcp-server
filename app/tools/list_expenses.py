from app.auth import get_request_owner_id
from app.mcp_instance import mcp
from app.services.expense_service import ExpenseService


@mcp.tool()
def list_expenses() -> list[dict]:
    """List this user's expenses sorted by date, newest first."""
    expenses = ExpenseService.list_expenses(owner_id=get_request_owner_id())
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