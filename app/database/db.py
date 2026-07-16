from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_connect_args = {"check_same_thread": False} if _is_sqlite else {}

# Pool settings — meaningful for PostgreSQL, ignored by SQLite
_pool_kwargs = (
    {}
    if _is_sqlite
    else {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }
)

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    connect_args=_connect_args,
    **_pool_kwargs,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()


def validate_connection() -> None:
    """Verify the database is reachable. Raises on failure."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))