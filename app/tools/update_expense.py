from datetime import date
from decimal import Decimal

from app.auth import get_request_owner_id, require_write_scope
from app.mcp_instance import mcp
from app.schemas.expense import ExpenseUpdate
from app.services.expense_service import ExpenseService


@mcp.tool()
def update_expense(
    expense_id: int,
    amount: Decimal | None = None,
    category: str | None = None,
    description: str | None = None,
    merchant: str | None = None,
    payment_method: str | None = None,
    currency: str | None = None,
    expense_date: str | None = None,
) -> dict:
    """Update this user's expense by ID. HTTP callers need expenses:write."""
    require_write_scope()
    parsed_date = date.fromisoformat(expense_date) if expense_date else None

    fields: dict = {}
    if amount is not None:
        fields["amount"] = amount
    if category is not None:
        fields["category"] = category
    if description is not None:
        fields["description"] = description
    if merchant is not None:
        fields["merchant"] = merchant
    if payment_method is not None:
        fields["payment_method"] = payment_method
    if currency is not None:
        fields["currency"] = currency
    if parsed_date is not None:
        fields["expense_date"] = parsed_date

    expense = ExpenseUpdate(**fields)
    updated = ExpenseService.update_expense(
        expense_id,
        expense,
        owner_id=get_request_owner_id(),
    )
    return {
        "message": "Expense updated successfully.",
        "expense_id": updated.id,
        "amount": float(updated.amount),
        "category": updated.category,
        "merchant": updated.merchant,
        "currency": updated.currency,
        "expense_date": str(updated.expense_date),
    }