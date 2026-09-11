import sys

from app.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

from app.config import settings
from app.database import db
from app.database import models  # noqa: F401 — registers models with Base


def startup() -> None:
    logger.info("Starting Expense MCP Server [env=%s]", settings.APP_ENV)

    try:
        db.validate_connection()
        logger.info("Database connection OK")
    except Exception as exc:
        logger.critical("Database connection failed: %s", exc)
        sys.exit(1)

    db.Base.metadata.create_all(bind=db.engine)
    logger.info("Database tables ready")


if __name__ == "__main__":
    startup()

    from app.server import mcp  # noqa — registers all tools via side-effect imports

    transport = settings.TRANSPORT.lower()
    logger.info("Transport: %s | Host: %s | Port: %s", transport, settings.HOST, settings.PORT)

    mcp.run(transport=transport)