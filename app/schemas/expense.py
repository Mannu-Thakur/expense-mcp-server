from datetime import date
from pydantic import BaseModel, Field


class ExpenseCreate(BaseModel):
    amount: float = Field(..., gt=0)
    category: str
    description: str | None = None
    merchant: str | None = None
    payment_method: str | None = None
    currency: str = "INR"
    expense_date: date


class ExpenseUpdate(BaseModel):
    amount: float | None = Field(default=None, gt=0)
    category: str | None = None
    description: str | None = None
    merchant: str | None = None
    payment_method: str | None = None
    currency: str | None = None
    expense_date: date | None = None