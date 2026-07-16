from datetime import date

from app.database.db import SessionLocal
from app.database.models import Expense
from app.exceptions import ExpenseNotFoundError
from app.logging_config import get_logger
from app.repositories.expense_repository import ExpenseRepository
from app.schemas.expense import ExpenseCreate, ExpenseUpdate

logger = get_logger(__name__)


class ExpenseService:

    @staticmethod
    def add_expense(expense: ExpenseCreate) -> Expense:
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
            )
            saved = ExpenseRepository.create(db, new_expense)
            logger.info("Created expense id=%s amount=%.2f", saved.id, saved.amount)
            return saved
        finally:
            db.close()

    @staticmethod
    def list_expenses() -> list[Expense]:
        db = SessionLocal()
        try:
            return ExpenseRepository.get_all(db)
        finally:
            db.close()

    @staticmethod
    def update_expense(expense_id: int, expense_update: ExpenseUpdate) -> Expense:
        db = SessionLocal()
        try:
            expense = ExpenseRepository.get_by_id(db, expense_id)
            if expense is None:
                raise ExpenseNotFoundError(expense_id)

            for field, value in expense_update.model_dump(exclude_unset=True).items():
                setattr(expense, field, value)

            updated = ExpenseRepository.update(db, expense)
            logger.info("Updated expense id=%s", expense_id)
            return updated
        finally:
            db.close()

    @staticmethod
    def delete_expense(expense_id: int) -> dict:
        db = SessionLocal()
        try:
            expense = ExpenseRepository.get_by_id(db, expense_id)
            if expense is None:
                raise ExpenseNotFoundError(expense_id)

            ExpenseRepository.delete(db, expense)
            logger.info("Deleted expense id=%s", expense_id)
            return {"message": "Expense deleted successfully.", "expense_id": expense_id}
        finally:
            db.close()

    @staticmethod
    def search_expenses(query: str) -> list[Expense]:
        db = SessionLocal()
        try:
            return ExpenseRepository.search(db, query)
        finally:
            db.close()

    @staticmethod
    def monthly_summary() -> dict:
        db = SessionLocal()
        try:
            result = ExpenseRepository.monthly_summary(db)
            today = date.today()
            return {
                "month": today.strftime("%B %Y"),
                "total_expense": float(result[0] or 0),
                "transaction_count": result[1] or 0,
                "average_expense": round(float(result[2] or 0), 2),
                "highest_expense": float(result[3] or 0),
            }
        finally:
            db.close()

    @staticmethod
    def category_summary() -> list[dict]:
        db = SessionLocal()
        try:
            rows = ExpenseRepository.category_summary(db)
            return [
                {
                    "category": row.category,
                    "total": float(row.total),
                    "transactions": row.transactions,
                }
                for row in rows
            ]
        finally:
            db.close()

    @staticmethod
    def top_merchants(limit: int = 5) -> list[dict]:
        db = SessionLocal()
        try:
            rows = ExpenseRepository.top_merchants(db, limit)
            return [
                {
                    "merchant": row.merchant,
                    "total": float(row.total),
                    "transactions": row.transactions,
                }
                for row in rows
            ]
        finally:
            db.close()