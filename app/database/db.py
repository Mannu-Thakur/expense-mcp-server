import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


def _get_clean_url(url: str) -> str:
    url = (url or "").strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


db_url = _get_clean_url(settings.DATABASE_URL)
_is_sqlite = db_url.startswith("sqlite")

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

try:
    engine = create_engine(
        db_url,
        echo=False,
        future=True,
        connect_args=_connect_args,
        **_pool_kwargs,
    )
except Exception as _e:
    logger.warning("Could not initialize engine for %s (%s). Falling back to SQLite.", db_url, _e)
    fallback_dir = Path("/app") if os.path.exists("/app") and os.access("/app", os.W_OK) else Path("/tmp")
    fallback_file = fallback_dir / "expenses.db"
    fallback_url = f"sqlite:///{fallback_file.as_posix()}"
    engine = create_engine(
        fallback_url,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
    )

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()


def switch_to_sqlite_fallback() -> None:
    global engine, SessionLocal
    fallback_dir = Path("/app") if os.path.exists("/app") and os.access("/app", os.W_OK) else Path("/tmp")
    fallback_file = fallback_dir / "expenses.db"
    fallback_url = f"sqlite:///{fallback_file.as_posix()}"
    logger.warning("Falling back to local SQLite database: %s", fallback_url)
    engine = create_engine(
        fallback_url,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
    )
    SessionLocal.configure(bind=engine)
    Base.metadata.create_all(bind=engine)


def validate_connection() -> None:
    """Verify the database is reachable. Automatically falls back to SQLite if primary DB is down."""
    global engine
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("Primary database unreachable: %s", exc)
        if not _is_sqlite:
            logger.warning("PostgreSQL unreachable. Activating SQLite fallback to ensure service starts.")
            switch_to_sqlite_fallback()
        else:
            raise exc