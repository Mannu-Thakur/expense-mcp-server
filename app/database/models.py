from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Integer, Numeric, String

from app.database.db import Base


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True)
    amount = Column(Numeric(18, 2), nullable=False)
    category = Column(String, nullable=False)
    description = Column(String, nullable=True)
    merchant = Column(String, nullable=True)
    payment_method = Column(String, nullable=True)
    currency = Column(String(3), nullable=False, default="INR", server_default="INR")
    expense_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    owner_id = Column(
        String(64),
        nullable=False,
        default="local",
        server_default="local",
        index=True,
    )
