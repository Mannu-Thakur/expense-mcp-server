from sqlalchemy import Numeric, create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


def _get_clean_url(url: str) -> str:
    clean_url = (url or "").strip()
    if clean_url.startswith("postgres://"):
        clean_url = clean_url.replace("postgres://", "postgresql://", 1)
    return clean_url


db_url = _get_clean_url(settings.DATABASE_URL)
_is_sqlite = db_url.startswith("sqlite")

_connect_args = {"check_same_thread": False} if _is_sqlite else {}
_pool_kwargs = (
    {}
    if _is_sqlite
    else {"pool_size": 5, "max_overflow": 10, "pool_pre_ping": True}
)

try:
    engine = create_engine(
        db_url,
        echo=False,
        future=True,
        connect_args=_connect_args,
        **_pool_kwargs,
    )
except Exception as exc:
    logger.error("Database engine initialization failed (%s).", type(exc).__name__)
    raise RuntimeError("Unable to configure the database engine.") from None

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def validate_database_configuration(target_engine=engine, app_env: str | None = None) -> None:
    """Reject an ephemeral or unsupported database for production deployments."""
    environment = (app_env or settings.APP_ENV).lower()
    dialect = target_engine.dialect.name
    if dialect not in {"sqlite", "postgresql"}:
        raise RuntimeError(f"Database dialect {dialect!r} is not supported.")
    if environment == "production" and dialect != "postgresql":
        raise RuntimeError("Production requires PostgreSQL; SQLite is only supported for local development.")


def validate_connection(target_engine=engine) -> None:
    """Fail startup when the configured database cannot be reached."""
    try:
        with target_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("Database connection check failed (%s).", type(exc).__name__)
        raise RuntimeError("Configured database is unavailable; startup aborted.") from exc


def _ensure_owner_index(target_engine, connection=None) -> None:
    statement = "CREATE INDEX IF NOT EXISTS ix_expenses_owner_id ON expenses(owner_id)"
    if connection is not None:
        connection.exec_driver_sql(statement)
        return
    with target_engine.begin() as conn:
        conn.exec_driver_sql(statement)


def migrate_schema(target_engine=engine) -> None:
    """Upgrade legacy expense tables without silently dropping unknown columns."""
    inspector = inspect(target_engine)
    if not inspector.has_table("expenses"):
        return

    columns = {column["name"]: column for column in inspector.get_columns("expenses")}
    dialect = target_engine.dialect.name

    if dialect == "sqlite":
        expected_columns = {
            "id",
            "amount",
            "category",
            "description",
            "merchant",
            "payment_method",
            "currency",
            "expense_date",
            "created_at",
            "owner_id",
        }
        required_columns = {"id", "amount", "category", "expense_date"}
        missing_required = required_columns - set(columns)
        if missing_required:
            raise RuntimeError(
                "Cannot migrate the SQLite expenses table; required columns are missing: "
                + ", ".join(sorted(missing_required))
            )

        with target_engine.connect() as conn:
            invalid_rows = conn.exec_driver_sql(
                "SELECT COUNT(*) FROM expenses "
                "WHERE amount IS NULL OR category IS NULL OR expense_date IS NULL"
            ).scalar_one()
            long_currency_rows = (
                conn.exec_driver_sql(
                    "SELECT COUNT(*) FROM expenses "
                    "WHERE LENGTH(TRIM(CAST(currency AS TEXT))) > 3"
                ).scalar_one()
                if "currency" in columns
                else 0
            )
        if invalid_rows:
            raise RuntimeError(
                "Cannot migrate SQLite expenses containing NULL amount, category, or expense_date values."
            )
        if long_currency_rows:
            raise RuntimeError(
                "Cannot migrate SQLite expenses with currency values longer than three characters."
            )

        amount_type = columns["amount"]["type"]
        fixed_amount = (
            isinstance(amount_type, Numeric)
            and amount_type.precision == 18
            and amount_type.scale == 2
        )
        owner_column = columns.get("owner_id")
        currency_column = columns.get("currency")
        needs_rebuild = (
            not fixed_amount
            or any(columns[name].get("nullable", True) for name in required_columns)
            or owner_column is None
            or owner_column.get("nullable", True)
            or currency_column is None
            or currency_column.get("nullable", True)
            or getattr(currency_column.get("type"), "length", None) != 3
        )

        if needs_rebuild:
            unknown_columns = set(columns) - expected_columns
            if unknown_columns:
                raise RuntimeError(
                    "Cannot rebuild the SQLite expenses table because it has additional columns: "
                    + ", ".join(sorted(unknown_columns))
                )
            temporary_table = "expenses_migration_new"
            if inspector.has_table(temporary_table):
                raise RuntimeError(
                    f"Found leftover table {temporary_table!r}; inspect it before retrying migration."
                )

            owner_expr = (
                "COALESCE(NULLIF(owner_id, ''), 'local')"
                if "owner_id" in columns
                else "'local'"
            )
            currency_expr = (
                "COALESCE(NULLIF(UPPER(TRIM(CAST(currency AS TEXT))), ''), 'INR')"
                if "currency" in columns
                else "'INR'"
            )
            currency_for_amount = "currency" if "currency" in columns else "'INR'"
            description_expr = "description" if "description" in columns else "NULL"
            merchant_expr = "merchant" if "merchant" in columns else "NULL"
            payment_expr = "payment_method" if "payment_method" in columns else "NULL"
            created_expr = "created_at" if "created_at" in columns else "NULL"

            with target_engine.begin() as conn:
                conn.exec_driver_sql(
                    f"""
                    CREATE TABLE {temporary_table} (
                        id INTEGER NOT NULL PRIMARY KEY,
                        amount NUMERIC(18, 2) NOT NULL,
                        category VARCHAR NOT NULL,
                        description VARCHAR,
                        merchant VARCHAR,
                        payment_method VARCHAR,
                        currency VARCHAR(3) NOT NULL DEFAULT 'INR',
                        expense_date DATE NOT NULL,
                        created_at DATETIME,
                        owner_id VARCHAR(64) NOT NULL DEFAULT 'local'
                    )
                    """
                )
                conn.exec_driver_sql(
                    f"""
                    INSERT INTO {temporary_table}
                        (id, amount, category, description, merchant, payment_method,
                         currency, expense_date, created_at, owner_id)
                    SELECT id,
                           ROUND(CAST(amount AS NUMERIC),
                                 CASE WHEN UPPER(TRIM(CAST(COALESCE({currency_for_amount}, 'INR') AS TEXT))) = 'JPY' THEN 0 ELSE 2 END),
                           category,
                           {description_expr},
                           {merchant_expr},
                           {payment_expr},
                           {currency_expr},
                           expense_date,
                           {created_expr},
                           {owner_expr}
                    FROM expenses
                    """
                )
                conn.exec_driver_sql("DROP TABLE expenses")
                conn.exec_driver_sql(
                    f"ALTER TABLE {temporary_table} RENAME TO expenses"
                )

        with target_engine.begin() as conn:
            conn.exec_driver_sql(
                "UPDATE expenses SET currency = COALESCE(NULLIF(UPPER(TRIM(currency)), ''), 'INR')"
            )
            conn.exec_driver_sql(
                "UPDATE expenses SET amount = ROUND(CAST(amount AS NUMERIC), "
                "CASE WHEN currency = 'JPY' THEN 0 ELSE 2 END)"
            )
            conn.exec_driver_sql(
                "UPDATE expenses SET owner_id = COALESCE(NULLIF(TRIM(owner_id), ''), 'local')"
            )

        _ensure_owner_index(target_engine)
        return

    if dialect == "postgresql":
        missing_required = {"id", "amount", "category", "expense_date"} - set(columns)
        if missing_required:
            raise RuntimeError(
                "Cannot migrate the PostgreSQL expenses table; required columns are missing: "
                + ", ".join(sorted(missing_required))
            )

        with target_engine.connect() as conn:
            invalid_rows = conn.exec_driver_sql(
                "SELECT COUNT(*) FROM expenses "
                "WHERE amount IS NULL OR category IS NULL OR expense_date IS NULL"
            ).scalar_one()
            long_currency_rows = (
                conn.exec_driver_sql(
                    "SELECT COUNT(*) FROM expenses "
                    "WHERE LENGTH(BTRIM(currency::text)) > 3"
                ).scalar_one()
                if "currency" in columns
                else 0
            )
        if invalid_rows:
            raise RuntimeError(
                "Cannot migrate PostgreSQL expenses containing NULL amount, category, or expense_date values."
            )
        if long_currency_rows:
            raise RuntimeError(
                "Cannot migrate PostgreSQL expenses with currency values longer than three characters."
            )
        amount_type = columns["amount"]["type"]
        fixed_amount = (
            isinstance(amount_type, Numeric)
            and amount_type.precision == 18
            and amount_type.scale == 2
        )
        owner_column = columns.get("owner_id")
        currency_column = columns.get("currency")

        with target_engine.begin() as conn:
            if owner_column is None:
                conn.exec_driver_sql(
                    "ALTER TABLE expenses ADD COLUMN owner_id VARCHAR(64) NOT NULL DEFAULT 'local'"
                )
            else:
                conn.exec_driver_sql(
                    "UPDATE expenses SET owner_id = 'local' WHERE owner_id IS NULL OR owner_id = ''"
                )
                if owner_column.get("nullable", True):
                    conn.exec_driver_sql(
                        "ALTER TABLE expenses ALTER COLUMN owner_id SET NOT NULL"
                    )
                conn.exec_driver_sql(
                    "ALTER TABLE expenses ALTER COLUMN owner_id SET DEFAULT 'local'"
                )

            if currency_column is None:
                conn.exec_driver_sql(
                    "ALTER TABLE expenses ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'INR'"
                )
            else:
                conn.exec_driver_sql(
                    "UPDATE expenses SET currency = 'INR' "
                    "WHERE currency IS NULL OR BTRIM(currency::text) = ''"
                )
                conn.exec_driver_sql(
                    "UPDATE expenses SET currency = UPPER(BTRIM(currency::text)) "
                    "WHERE currency::text <> UPPER(BTRIM(currency::text))"
                )
                if getattr(currency_column.get("type"), "length", None) != 3:
                    conn.exec_driver_sql(
                        "ALTER TABLE expenses ALTER COLUMN currency TYPE VARCHAR(3) "
                        "USING currency::varchar(3)"
                    )
                if currency_column.get("nullable", True):
                    conn.exec_driver_sql(
                        "ALTER TABLE expenses ALTER COLUMN currency SET NOT NULL"
                    )
                conn.exec_driver_sql(
                    "ALTER TABLE expenses ALTER COLUMN currency SET DEFAULT 'INR'"
                )

            if not fixed_amount:
                conn.exec_driver_sql(
                    "ALTER TABLE expenses ALTER COLUMN amount TYPE NUMERIC(18, 2) "
                    "USING ROUND(amount::numeric, "
                    "CASE WHEN UPPER(COALESCE(currency, 'INR')) = 'JPY' THEN 0 ELSE 2 END)"
                )
            conn.exec_driver_sql(
                "UPDATE expenses SET amount = ROUND(amount, "
                "CASE WHEN currency = 'JPY' THEN 0 ELSE 2 END)"
            )
            for required_column in ("amount", "category", "expense_date"):
                conn.exec_driver_sql(
                    f"ALTER TABLE expenses ALTER COLUMN {required_column} SET NOT NULL"
                )
            _ensure_owner_index(target_engine, connection=conn)
        return

    raise RuntimeError(f"Database dialect {dialect!r} is not supported.")
