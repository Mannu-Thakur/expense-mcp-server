"""
Full test suite for the Expense MCP Server.

Covers:
  - Repository layer (CRUD + search + analytics)
  - Service layer (add, list, update, delete, search, summaries)
  - MCP tool functions (all 8 tools)
"""

from datetime import date, timedelta

import pytest

from app.database.models import Expense
from app.exceptions import ExpenseNotFoundError
from app.repositories.expense_repository import ExpenseRepository
from app.schemas.expense import ExpenseCreate, ExpenseUpdate
from app.services.expense_service import ExpenseService


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_expense(db, **kwargs) -> Expense:
    defaults = dict(
        amount=100.0,
        category="Food",
        description="Test expense",
        merchant="Test Merchant",
        payment_method="Cash",
        currency="INR",
        expense_date=date.today(),
    )
    defaults.update(kwargs)
    expense = Expense(**defaults)
    return ExpenseRepository.create(db, expense)


# ═════════════════════════════════════════════════════════════════════════════
# REPOSITORY TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestExpenseRepository:

    def test_create(self, db):
        e = make_expense(db, amount=200.0, category="Travel")
        assert e.id is not None
        assert e.amount == 200.0
        assert e.category == "Travel"

    def test_get_by_id(self, db):
        e = make_expense(db)
        fetched = ExpenseRepository.get_by_id(db, e.id)
        assert fetched is not None
        assert fetched.id == e.id

    def test_get_by_id_not_found(self, db):
        result = ExpenseRepository.get_by_id(db, 99999)
        assert result is None

    def test_get_all_ordered(self, db):
        today = date.today()
        make_expense(db, expense_date=today - timedelta(days=1), amount=50.0)
        make_expense(db, expense_date=today, amount=75.0)
        all_expenses = ExpenseRepository.get_all(db)
        assert len(all_expenses) >= 2
        # Most recent first
        assert all_expenses[0].expense_date >= all_expenses[1].expense_date

    def test_update(self, db):
        e = make_expense(db, amount=100.0)
        e.amount = 999.0
        updated = ExpenseRepository.update(db, e)
        assert updated.amount == 999.0

    def test_delete(self, db):
        e = make_expense(db)
        eid = e.id
        ExpenseRepository.delete(db, e)
        assert ExpenseRepository.get_by_id(db, eid) is None

    def test_search_by_category(self, db):
        make_expense(db, category="Groceries", description="Weekly shop")
        results = ExpenseRepository.search(db, "Groceries")
        assert any(e.category == "Groceries" for e in results)

    def test_search_by_description(self, db):
        make_expense(db, description="Coffee at Starbucks")
        results = ExpenseRepository.search(db, "Starbucks")
        assert len(results) >= 1

    def test_search_by_merchant(self, db):
        make_expense(db, merchant="Amazon")
        results = ExpenseRepository.search(db, "Amazon")
        assert any(e.merchant == "Amazon" for e in results)

    def test_search_no_match(self, db):
        results = ExpenseRepository.search(db, "XYZNONEXISTENT")
        assert results == []

    def test_monthly_summary(self, db):
        make_expense(db, amount=300.0, expense_date=date.today())
        result = ExpenseRepository.monthly_summary(db)
        assert result[0] is not None  # total
        assert result[1] >= 1          # count

    def test_category_summary(self, db):
        make_expense(db, category="Food", amount=100.0)
        make_expense(db, category="Food", amount=200.0)
        make_expense(db, category="Travel", amount=500.0)
        rows = ExpenseRepository.category_summary(db)
        categories = [r.category for r in rows]
        assert "Food" in categories
        assert "Travel" in categories

    def test_top_merchants(self, db):
        make_expense(db, merchant="Zomato", amount=150.0)
        make_expense(db, merchant="Zomato", amount=200.0)
        make_expense(db, merchant="Uber", amount=80.0)
        rows = ExpenseRepository.top_merchants(db, limit=2)
        assert len(rows) <= 2
        assert rows[0].merchant == "Zomato"


# ═════════════════════════════════════════════════════════════════════════════
# SERVICE TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestExpenseService:

    def test_add_expense(self):
        payload = ExpenseCreate(
            amount=250.0,
            category="Food",
            description="Lunch",
            merchant="Cafe",
            payment_method="UPI",
            currency="INR",
            expense_date=date.today(),
        )
        saved = ExpenseService.add_expense(payload)
        assert saved.id is not None
        assert saved.amount == 250.0
        assert saved.category == "Food"

    def test_list_expenses(self):
        payload = ExpenseCreate(
            amount=50.0,
            category="Misc",
            expense_date=date.today(),
        )
        ExpenseService.add_expense(payload)
        expenses = ExpenseService.list_expenses()
        assert len(expenses) >= 1

    def test_update_expense(self):
        payload = ExpenseCreate(
            amount=100.0,
            category="Health",
            expense_date=date.today(),
        )
        saved = ExpenseService.add_expense(payload)

        update = ExpenseUpdate(amount=999.0, category="Wellness")
        updated = ExpenseService.update_expense(saved.id, update)
        assert updated.amount == 999.0
        assert updated.category == "Wellness"

    def test_update_expense_not_found(self):
        with pytest.raises(ExpenseNotFoundError):
            ExpenseService.update_expense(99999, ExpenseUpdate(amount=1.0))

    def test_delete_expense(self):
        payload = ExpenseCreate(
            amount=10.0,
            category="Test",
            expense_date=date.today(),
        )
        saved = ExpenseService.add_expense(payload)
        result = ExpenseService.delete_expense(saved.id)
        assert result["expense_id"] == saved.id

    def test_delete_expense_not_found(self):
        with pytest.raises(ExpenseNotFoundError):
            ExpenseService.delete_expense(99999)

    def test_search_expenses(self):
        payload = ExpenseCreate(
            amount=75.0,
            category="Entertainment",
            description="Netflix subscription",
            expense_date=date.today(),
        )
        ExpenseService.add_expense(payload)
        results = ExpenseService.search_expenses("Netflix")
        assert len(results) >= 1

    def test_monthly_summary_shape(self):
        result = ExpenseService.monthly_summary()
        assert "month" in result
        assert "total_expense" in result
        assert "transaction_count" in result
        assert "average_expense" in result
        assert "highest_expense" in result

    def test_category_summary_shape(self):
        ExpenseService.add_expense(
            ExpenseCreate(amount=100.0, category="Food", expense_date=date.today())
        )
        result = ExpenseService.category_summary()
        assert isinstance(result, list)
        if result:
            assert "category" in result[0]
            assert "total" in result[0]
            assert "transactions" in result[0]

    def test_top_merchants_shape(self):
        ExpenseService.add_expense(
            ExpenseCreate(
                amount=200.0,
                category="Food",
                merchant="BigBasket",
                expense_date=date.today(),
            )
        )
        result = ExpenseService.top_merchants(limit=3)
        assert isinstance(result, list)
        if result:
            assert "merchant" in result[0]
            assert "total" in result[0]
            assert "transactions" in result[0]


# ═════════════════════════════════════════════════════════════════════════════
# TOOL TESTS (call the actual @mcp.tool functions directly)
# ═════════════════════════════════════════════════════════════════════════════

class TestTools:

    def _import_tools(self):
        """Import tools lazily so conftest patches are already applied."""
        from app.tools.add_expense import add_expense
        from app.tools.list_expenses import list_expenses
        from app.tools.update_expense import update_expense
        from app.tools.delete_expense import delete_expense
        from app.tools.search_expenses import search_expenses
        from app.tools.monthly_summary import monthly_summary
        from app.tools.category_summary import category_summary
        from app.tools.top_merchants import top_merchants
        return (
            add_expense, list_expenses, update_expense, delete_expense,
            search_expenses, monthly_summary, category_summary, top_merchants,
        )

    def test_add_expense_tool(self):
        add_expense, *_ = self._import_tools()
        result = add_expense(
            amount=500.0,
            category="Shopping",
            description="Groceries",
            merchant="DMart",
            payment_method="Card",
            currency="INR",
            expense_date=date.today().isoformat(),
        )
        assert result["expense_id"] is not None
        assert result["amount"] == 500.0
        assert result["category"] == "Shopping"

    def test_list_expenses_tool(self):
        add_expense, list_expenses, *_ = self._import_tools()
        add_expense(amount=100.0, category="Food")
        result = list_expenses()
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_update_expense_tool(self):
        add_expense, _, update_expense, *_ = self._import_tools()
        added = add_expense(amount=100.0, category="Food")
        result = update_expense(
            expense_id=added["expense_id"],
            amount=250.0,
            category="Dining",
        )
        assert result["amount"] == 250.0
        assert result["category"] == "Dining"

    def test_delete_expense_tool(self):
        add_expense, _, __, delete_expense, *_ = self._import_tools()
        added = add_expense(amount=50.0, category="Misc")
        result = delete_expense(expense_id=added["expense_id"])
        assert result["expense_id"] == added["expense_id"]

    def test_search_expenses_tool(self):
        add_expense, _, __, ___, search_expenses, *_ = self._import_tools()
        add_expense(amount=200.0, category="Transport", merchant="Uber")
        result = search_expenses(query="Uber")
        assert any(e["merchant"] == "Uber" for e in result)

    def test_monthly_summary_tool(self):
        *_, monthly_summary, __, ___ = self._import_tools()
        result = monthly_summary()
        assert "month" in result
        assert isinstance(result["total_expense"], float)

    def test_category_summary_tool(self):
        add_expense, *_, category_summary, _ = self._import_tools()
        add_expense(amount=100.0, category="Bills")
        result = category_summary()
        assert isinstance(result, list)

    def test_top_merchants_tool(self):
        add_expense, *_, top_merchants = self._import_tools()
        add_expense(amount=300.0, category="Food", merchant="Swiggy")
        result = top_merchants(limit=3)
        assert isinstance(result, list)
