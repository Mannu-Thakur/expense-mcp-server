from datetime import date, datetime, timezone

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.auth import LOCAL_OWNER_ID
from app.database.models import Expense


class ExpenseRepository:
    @staticmethod
    def create(db: Session, expense: Expense) -> Expense:
        db.add(expense)
        db.commit()
        db.refresh(expense)
        return expense

    @staticmethod
    def get_all(db: Session, owner_id: str = LOCAL_OWNER_ID) -> list[Expense]:
        return (
            db.query(Expense)
            .filter(Expense.owner_id == owner_id)
            .order_by(Expense.expense_date.desc(), Expense.id.desc())
            .all()
        )

    @staticmethod
    def get_by_id(
        db: Session,
        expense_id: int,
        owner_id: str = LOCAL_OWNER_ID,
    ) -> Expense | None:
        return (
            db.query(Expense)
            .filter(Expense.id == expense_id, Expense.owner_id == owner_id)
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
    def search(
        db: Session,
        query: str,
        owner_id: str = LOCAL_OWNER_ID,
    ) -> list[Expense]:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        return (
            db.query(Expense)
            .filter(
                Expense.owner_id == owner_id,
                or_(
                    Expense.category.ilike(pattern, escape="\\"),
                    Expense.description.ilike(pattern, escape="\\"),
                    Expense.merchant.ilike(pattern, escape="\\"),
                ),
            )
            .order_by(Expense.expense_date.desc(), Expense.id.desc())
            .all()
        )

    @staticmethod
    def monthly_summary_by_currency(
        db: Session,
        owner_id: str = LOCAL_OWNER_ID,
        today: date | None = None,
    ) -> list:
        today = today or datetime.now(timezone.utc).date()
        start = date(today.year, today.month, 1)
        next_start = (
            date(today.year + 1, 1, 1)
            if today.month == 12
            else date(today.year, today.month + 1, 1)
        )
        return (
            db.query(
                Expense.currency.label("currency"),
                func.sum(Expense.amount).label("total"),
                func.count(Expense.id).label("transactions"),
                func.avg(Expense.amount).label("average"),
                func.max(Expense.amount).label("highest"),
            )
            .filter(
                Expense.owner_id == owner_id,
                Expense.expense_date >= start,
                Expense.expense_date < next_start,
            )
            .group_by(Expense.currency)
            .order_by(Expense.currency)
            .all()
        )

    @staticmethod
    def monthly_summary(db: Session, owner_id: str = LOCAL_OWNER_ID) -> tuple:
        """Compatibility summary; amount metrics are omitted for mixed currencies."""
        rows = ExpenseRepository.monthly_summary_by_currency(db, owner_id)
        if not rows:
            return (None, 0, None, None)
        if len(rows) == 1:
            row = rows[0]
            return (row.total, row.transactions, row.average, row.highest)
        return (None, sum(row.transactions for row in rows), None, None)

    @staticmethod
    def category_summary(db: Session, owner_id: str = LOCAL_OWNER_ID) -> list:
        return (
            db.query(
                Expense.category.label("category"),
                Expense.currency.label("currency"),
                func.sum(Expense.amount).label("total"),
                func.count(Expense.id).label("transactions"),
            )
            .filter(Expense.owner_id == owner_id)
            .group_by(Expense.category, Expense.currency)
            .order_by(func.sum(Expense.amount).desc(), Expense.currency, Expense.category)
            .all()
        )

    @staticmethod
    def top_merchants(
        db: Session,
        limit: int = 5,
        owner_id: str = LOCAL_OWNER_ID,
    ) -> list:
        return (
            db.query(
                Expense.merchant.label("merchant"),
                Expense.currency.label("currency"),
                func.sum(Expense.amount).label("total"),
                func.count(Expense.id).label("transactions"),
            )
            .filter(Expense.owner_id == owner_id, Expense.merchant.isnot(None))
            .group_by(Expense.merchant, Expense.currency)
            .order_by(func.sum(Expense.amount).desc(), Expense.currency, Expense.merchant)
            .limit(limit)
            .all()
        )