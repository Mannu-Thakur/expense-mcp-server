from datetime import datetime, timezone
from decimal import Decimal

from app.auth import LOCAL_OWNER_ID
from app.database.db import SessionLocal
from app.database.models import Expense
from app.exceptions import ExpenseNotFoundError
from app.logging_config import get_logger
from app.repositories.expense_repository import ExpenseRepository
from app.schemas.expense import ExpenseCreate, ExpenseUpdate
from app.utils.currency import validate_amount_currency

logger = get_logger(__name__)


def _as_number(value: Decimal | int | float | None) -> float:
    return float(value or 0)


class ExpenseService:
    @staticmethod
    def add_expense(
        expense: ExpenseCreate,
        owner_id: str = LOCAL_OWNER_ID,
    ) -> Expense:
        db = SessionLocal()
        try:
            new_expense = Expense(
                amount=expense.amount,
                category=expense.category,
                description=expense.description,
                merchant=expense.merchant,
                payment_method=expense.payment_method,
                currency=expense.currency,
                expense_date=expense.expense_date,
                owner_id=owner_id,
            )
            saved = ExpenseRepository.create(db, new_expense)
            logger.info("Created expense id=%s", saved.id)
            return saved
        finally:
            db.close()

    @staticmethod
    def list_expenses(owner_id: str = LOCAL_OWNER_ID) -> list[Expense]:
        db = SessionLocal()
        try:
            return ExpenseRepository.get_all(db, owner_id)
        finally:
            db.close()

    @staticmethod
    def update_expense(
        expense_id: int,
        expense_update: ExpenseUpdate,
        owner_id: str = LOCAL_OWNER_ID,
    ) -> Expense:
        db = SessionLocal()
        try:
            expense = ExpenseRepository.get_by_id(db, expense_id, owner_id)
            if expense is None:
                raise ExpenseNotFoundError(expense_id)

            updates = expense_update.model_dump(exclude_unset=True)
            next_amount = updates.get("amount", expense.amount)
            next_currency = updates.get("currency", expense.currency)
            if next_amount is not None and next_currency is not None:
                validate_amount_currency(Decimal(str(next_amount)), next_currency)

            for field, value in updates.items():
                setattr(expense, field, value)

            updated = ExpenseRepository.update(db, expense)
            logger.info("Updated expense id=%s", expense_id)
            return updated
        finally:
            db.close()

    @staticmethod
    def delete_expense(
        expense_id: int,
        owner_id: str = LOCAL_OWNER_ID,
    ) -> dict:
        db = SessionLocal()
        try:
            expense = ExpenseRepository.get_by_id(db, expense_id, owner_id)
            if expense is None:
                raise ExpenseNotFoundError(expense_id)

            ExpenseRepository.delete(db, expense)
            logger.info("Deleted expense id=%s", expense_id)
            return {"message": "Expense deleted successfully.", "expense_id": expense_id}
        finally:
            db.close()

    @staticmethod
    def search_expenses(query: str, owner_id: str = LOCAL_OWNER_ID) -> list[Expense]:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("Search query must not be blank.")
        if len(normalized_query) > 200:
            raise ValueError("Search query must be at most 200 characters.")
        db = SessionLocal()
        try:
            return ExpenseRepository.search(db, normalized_query, owner_id)
        finally:
            db.close()

    @staticmethod
    def monthly_summary(owner_id: str = LOCAL_OWNER_ID) -> dict:
        today = datetime.now(timezone.utc).date()
        db = SessionLocal()
        try:
            rows = ExpenseRepository.monthly_summary_by_currency(
                db,
                owner_id,
                today=today,
            )
            currency_breakdown = [
                {
                    "currency": row.currency,
                    "total_expense": _as_number(row.total),
                    "transaction_count": row.transactions,
                    "average_expense": round(_as_number(row.average), 2),
                    "highest_expense": _as_number(row.highest),
                }
                for row in rows
            ]
            result = {
                "month": today.strftime("%B %Y"),
                "transaction_count": sum(row.transactions for row in rows),
                "currency_breakdown": currency_breakdown,
            }
            if len(rows) == 1:
                row = rows[0]
                result.update(
                    {
                        "total_expense": _as_number(row.total),
                        "average_expense": round(_as_number(row.average), 2),
                        "highest_expense": _as_number(row.highest),
                    }
                )
            elif not rows:
                result.update(
                    {
                        "total_expense": 0.0,
                        "average_expense": 0.0,
                        "highest_expense": 0.0,
                    }
                )
            else:
                result.update(
                    {
                        "total_expense": None,
                        "average_expense": None,
                        "highest_expense": None,
                    }
                )
            return result
        finally:
            db.close()

    @staticmethod
    def category_summary(owner_id: str = LOCAL_OWNER_ID) -> list[dict]:
        db = SessionLocal()
        try:
            rows = ExpenseRepository.category_summary(db, owner_id)
            return [
                {
                    "category": row.category,
                    "currency": row.currency,
                    "total": _as_number(row.total),
                    "transactions": row.transactions,
                }
                for row in rows
            ]
        finally:
            db.close()

    @staticmethod
    def top_merchants(
        limit: int = 5,
        owner_id: str = LOCAL_OWNER_ID,
    ) -> list[dict]:
        if not 1 <= limit <= 50:
            raise ValueError("Limit must be between 1 and 50.")
        db = SessionLocal()
        try:
            rows = ExpenseRepository.top_merchants(db, limit, owner_id)
            return [
                {
                    "merchant": row.merchant,
                    "currency": row.currency,
                    "total": _as_number(row.total),
                    "transactions": row.transactions,
                }
                for row in rows
            ]
        finally:
            db.close()