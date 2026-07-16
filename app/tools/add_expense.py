from datetime import date

from app.mcp_instance import mcp
from app.schemas.expense import ExpenseCreate
from app.services.expense_service import ExpenseService


@mcp.tool()
def add_expense(
    amount: float,
    category: str,
    description: str = "",
    merchant: str = "",
    payment_method: str = "Cash",
    currency: str = "INR",
    expense_date: str = "",
) -> dict:
    """Add a new expense."""
    parsed_date = (
        date.fromisoformat(expense_date) if expense_date else date.today()
    )

    expense = ExpenseCreate(
        amount=amount,
        category=category,
        description=description or None,
        merchant=merchant or None,
        payment_method=payment_method,
        currency=currency,
        expense_date=parsed_date,
    )

    saved = ExpenseService.add_expense(expense)

    return {
        "message": "Expense added successfully.",
        "expense_id": saved.id,
        "amount": saved.amount,
        "category": saved.category,
        "merchant": saved.merchant,
        "currency": saved.currency,
        "expense_date": str(saved.expense_date),
    }