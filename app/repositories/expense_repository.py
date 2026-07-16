from datetime import date

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database.models import Expense


class ExpenseRepository:

    @staticmethod
    def create(db: Session, expense: Expense) -> Expense:
        db.add(expense)
        db.commit()
        db.refresh(expense)
        return expense

    @staticmethod
    def get_all(db: Session) -> list[Expense]:
        return (
            db.query(Expense)
            .order_by(Expense.expense_date.desc())
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, expense_id: int) -> Expense | None:
        return (
            db.query(Expense)
            .filter(Expense.id == expense_id)
            .first()
        )

    @staticmethod
    def update(db: Session, expense: Expense) -> Expense:
        db.commit()
        db.refresh(expense)
        return expense

    @staticmethod
    def delete(db: Session, expense: Expense) -> None:
        db.delete(expense)
        db.commit()

    @staticmethod
    def search(db: Session, query: str) -> list[Expense]:
        pattern = f"%{query}%"
        return (
            db.query(Expense)
            .filter(
                or_(
                    Expense.category.ilike(pattern),
                    Expense.description.ilike(pattern),
                    Expense.merchant.ilike(pattern),
                )
            )
            .all()
        )

    @staticmethod
    def monthly_summary(db: Session) -> tuple:
        today = date.today()
        start = date(today.year, today.month, 1)
        return (
            db.query(
                func.sum(Expense.amount),
                func.count(Expense.id),
                func.avg(Expense.amount),
                func.max(Expense.amount),
            )
            .filter(Expense.expense_date >= start)
            .first()
        )

    @staticmethod
    def category_summary(db: Session) -> list:
        return (
            db.query(
                Expense.category,
                func.sum(Expense.amount).label("total"),
                func.count(Expense.id).label("transactions"),
            )
            .group_by(Expense.category)
            .order_by(func.sum(Expense.amount).desc())
            .all()
        )

    @staticmethod
    def top_merchants(db: Session, limit: int = 5) -> list:
        return (
            db.query(
                Expense.merchant,
                func.sum(Expense.amount).label("total"),
                func.count(Expense.id).label("transactions"),
            )
            .filter(Expense.merchant.isnot(None))
            .group_by(Expense.merchant)
            .order_by(func.sum(Expense.amount).desc())
            .limit(limit)
            .all()
        )