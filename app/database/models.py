from sqlalchemy import Column, Integer, Float, String, Date, DateTime
from datetime import datetime, timezone

from app.database.db import Base


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    description = Column(String, nullable=True)
    merchant = Column(String, nullable=True)
    payment_method = Column(String, nullable=True)
    currency = Column(String, nullable=True, default="INR")
    expense_date = Column(Date, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )