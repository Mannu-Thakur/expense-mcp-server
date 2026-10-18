import os
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text

from app.database.db import migrate_schema, validate_database_configuration


def make_legacy_sqlite_engine():
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            CREATE TABLE expenses (
                id INTEGER NOT NULL PRIMARY KEY,
                amount FLOAT NOT NULL,
                category VARCHAR NOT NULL,
                description VARCHAR,
                merchant VARCHAR,
                payment_method VARCHAR,
                currency VARCHAR,
                expense_date DATE NOT NULL,
                created_at DATETIME
            )
            """
        )
        conn.exec_driver_sql(
            """
            INSERT INTO expenses
                (id, amount, category, description, merchant, payment_method,
                 currency, expense_date, created_at)
            VALUES
                (1, 12.349, 'Food', 'Lunch', 'Cafe', 'Cash', ' usd ', '2026-01-02', NULL),
                (2, 1.5, 'Travel', NULL, NULL, 'Cash', 'jpy', '2026-01-03', NULL),
                (3, 1.009, 'Other', NULL, NULL, 'Cash', '', '2026-01-04', NULL)
            """
        )
    return engine


def test_sqlite_migration_preserves_rows_normalizes_values_and_is_idempotent():
    engine = make_legacy_sqlite_engine()
    try:
        migrate_schema(engine)
        migrate_schema(engine)

        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT id, amount, currency, owner_id FROM expenses ORDER BY id")
            ).all()
        assert [(row.id, Decimal(str(row.amount)), row.currency, row.owner_id) for row in rows] == [
            (1, Decimal("12.35"), "USD", "local"),
            (2, Decimal("2"), "JPY", "local"),
            (3, Decimal("1.01"), "INR", "local"),
        ]

        columns = {column["name"]: column for column in inspect(engine).get_columns("expenses")}
        assert columns["amount"]["type"].precision == 18
        assert columns["amount"]["type"].scale == 2
        assert columns["currency"]["nullable"] is False
        assert columns["owner_id"]["nullable"] is False
        assert "ix_expenses_owner_id" in {
            index["name"] for index in inspect(engine).get_indexes("expenses")
        }
    finally:
        engine.dispose()


def test_sqlite_migration_refuses_to_drop_unrecognized_columns():
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE expenses (id INTEGER PRIMARY KEY, amount FLOAT NOT NULL, "
            "category VARCHAR NOT NULL, expense_date DATE NOT NULL, custom_data TEXT)"
        )
        conn.exec_driver_sql(
            "INSERT INTO expenses (id, amount, category, expense_date, custom_data) "
            "VALUES (1, 1.0, 'Food', '2026-01-02', 'preserve me')"
        )

    with pytest.raises(RuntimeError, match="additional columns: custom_data"):
        migrate_schema(engine)

    with engine.connect() as conn:
        assert conn.execute(text("SELECT custom_data FROM expenses WHERE id=1")).scalar_one() == "preserve me"
    engine.dispose()


def test_sqlite_migration_refuses_to_truncate_invalid_currency_values():
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE expenses (id INTEGER PRIMARY KEY, amount FLOAT NOT NULL, "
            "category VARCHAR NOT NULL, currency VARCHAR, expense_date DATE NOT NULL)"
        )
        conn.exec_driver_sql(
            "INSERT INTO expenses (id, amount, category, currency, expense_date) "
            "VALUES (1, 10, 'Food', 'INDIA', '2026-01-02')"
        )

    with pytest.raises(RuntimeError, match="longer than three characters"):
        migrate_schema(engine)

    with engine.connect() as conn:
        assert conn.execute(text("SELECT currency FROM expenses WHERE id=1")).scalar_one() == "INDIA"
    engine.dispose()


def test_sqlite_migration_refuses_null_required_ledger_values():
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE expenses (id INTEGER PRIMARY KEY, amount FLOAT, "
            "category VARCHAR, expense_date DATE)"
        )
        conn.exec_driver_sql(
            "INSERT INTO expenses (id, amount, category, expense_date) "
            "VALUES (1, NULL, 'Food', '2026-01-02')"
        )

    with pytest.raises(RuntimeError, match="containing NULL amount"):
        migrate_schema(engine)

    with engine.connect() as conn:
        assert conn.execute(text("SELECT amount FROM expenses WHERE id=1")).scalar_one() is None
    engine.dispose()


def test_production_configuration_requires_postgresql():
    sqlite_engine = create_engine("sqlite:///:memory:")
    with pytest.raises(RuntimeError, match="Production requires PostgreSQL"):
        validate_database_configuration(sqlite_engine, "production")
    validate_database_configuration(sqlite_engine, "development")
    sqlite_engine.dispose()


@pytest.mark.skipif(not os.getenv("TEST_POSTGRES_URL"), reason="TEST_POSTGRES_URL is not configured")
def test_postgresql_migration_runs_against_a_legacy_schema():
    database_url = os.environ["TEST_POSTGRES_URL"]
    schema_name = f"expense_migration_{uuid4().hex}"
    admin_engine = create_engine(database_url, future=True)
    with admin_engine.begin() as conn:
        conn.exec_driver_sql(f'CREATE SCHEMA "{schema_name}"')

    migration_engine = create_engine(
        database_url,
        future=True,
        connect_args={"options": f"-csearch_path={schema_name}"},
    )
    try:
        with migration_engine.begin() as conn:
            conn.exec_driver_sql(
                """
                CREATE TABLE expenses (
                    id INTEGER NOT NULL PRIMARY KEY,
                    amount DOUBLE PRECISION NOT NULL,
                    category VARCHAR NOT NULL,
                    description VARCHAR,
                    merchant VARCHAR,
                    payment_method VARCHAR,
                    currency VARCHAR,
                    expense_date DATE NOT NULL,
                    created_at TIMESTAMP
                )
                """
            )
            conn.exec_driver_sql(
                """
                INSERT INTO expenses
                    (id, amount, category, description, merchant, payment_method,
                     currency, expense_date, created_at)
                VALUES
                    (1, 12.349, 'Food', 'Lunch', 'Cafe', 'Cash', ' usd ', '2026-01-02', NULL),
                    (2, 1.5, 'Travel', NULL, NULL, 'Cash', 'jpy', '2026-01-03', NULL),
                    (3, 1.009, 'Other', NULL, NULL, 'Cash', '', '2026-01-04', NULL)
                """
            )

        migrate_schema(migration_engine)
        migrate_schema(migration_engine)

        with migration_engine.connect() as conn:
            rows = conn.execute(
                text("SELECT id, amount, currency, owner_id FROM expenses ORDER BY id")
            ).all()
        assert [(row.id, row.amount, row.currency, row.owner_id) for row in rows] == [
            (1, Decimal("12.35"), "USD", "local"),
            (2, Decimal("2.00"), "JPY", "local"),
            (3, Decimal("1.01"), "INR", "local"),
        ]

        columns = {column["name"]: column for column in inspect(migration_engine).get_columns("expenses")}
        assert columns["amount"]["type"].precision == 18
        assert columns["amount"]["type"].scale == 2
        assert columns["currency"]["type"].length == 3
        assert columns["currency"]["nullable"] is False
        assert columns["owner_id"]["nullable"] is False
        assert "ix_expenses_owner_id" in {
            index["name"] for index in inspect(migration_engine).get_indexes("expenses")
        }
    finally:
        migration_engine.dispose()
        with admin_engine.begin() as conn:
            conn.exec_driver_sql(f'DROP SCHEMA "{schema_name}" CASCADE')
        admin_engine.dispose()
