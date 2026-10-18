from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.utils.currency import normalize_currency, validate_amount_currency


class ExpenseCreate(BaseModel):
    amount: Decimal = Field(..., gt=Decimal("0"), max_digits=18, decimal_places=2)
    category: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    merchant: str | None = Field(default=None, max_length=200)
    payment_method: str | None = Field(default=None, max_length=100)
    currency: str = "INR"
    expense_date: date

    @field_validator("category")
    @classmethod
    def clean_category(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Category must not be blank.")
        return value

    @field_validator("currency")
    @classmethod
    def clean_currency(cls, value: str) -> str:
        value = normalize_currency(value)
        validate_amount_currency(Decimal("1"), value)
        return value

    @model_validator(mode="after")
    def validate_amount_precision(self):
        validate_amount_currency(self.amount, self.currency)
        return self


class ExpenseUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=18, decimal_places=2)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    merchant: str | None = Field(default=None, max_length=200)
    payment_method: str | None = Field(default=None, max_length=100)
    currency: str | None = None
    expense_date: date | None = None

    @field_validator("category")
    @classmethod
    def clean_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Category must not be blank.")
        return value

    @field_validator("currency")
    @classmethod
    def clean_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = normalize_currency(value)
        validate_amount_currency(Decimal("1"), value)
        return value

    @model_validator(mode="after")
    def validate_amount_precision_when_currency_is_present(self):
        for field in ("amount", "category", "currency", "expense_date"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} must not be null.")
        if self.amount is not None and self.currency is not None:
            validate_amount_currency(self.amount, self.currency)
        return self