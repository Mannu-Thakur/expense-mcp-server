import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.db import Base
from app.database import models  # noqa: F401 — registers models


# ── In-memory SQLite engine for tests ─────────────────────────────────────────

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture(scope="function")
def db(engine):
    """Fresh session per test, rolled back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def override_db(db, monkeypatch):
    """
    Patch SessionLocal in the service layer so all service calls
    use the test session instead of the real database.
    """
    import app.services.expense_service as svc_module

    monkeypatch.setattr(
        svc_module,
        "SessionLocal",
        lambda: db,
    )
