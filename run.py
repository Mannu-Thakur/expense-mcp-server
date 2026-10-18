from app.logging_config import setup_logging, get_logger
from app.config import settings
from app.database import db
from app.database import models  # noqa: F401 — registers models with Base

setup_logging()
logger = get_logger(__name__)


def startup() -> None:
    logger.info("Starting Expense MCP Server [env=%s]", settings.APP_ENV)
    transport = settings.TRANSPORT.lower()
    if transport not in {"stdio", "streamable-http"}:
        logger.critical("Unsupported transport configuration.")
        raise SystemExit(1)

    try:
        db.validate_database_configuration()
    except RuntimeError as exc:
        logger.critical("Database configuration is invalid: %s", exc)
        raise SystemExit(1) from None

    try:
        settings.oauth_config(required=transport != "stdio")
    except ValueError as exc:
        logger.critical("HTTP authentication configuration is invalid: %s", exc)
        raise SystemExit(1) from None

    try:
        db.validate_connection()
        db.migrate_schema()
        db.Base.metadata.create_all(bind=db.engine)
    except Exception as exc:
        logger.critical("Database startup failed (%s); service will not start.", type(exc).__name__)
        raise SystemExit(1) from None

    logger.info("Database connection and schema are ready")


if __name__ == "__main__":
    startup()

    from app.server import mcp  # noqa — registers all tools via side-effect imports

    transport = settings.TRANSPORT.lower()
    logger.info("Transport: %s | Host: %s | Port: %s", transport, settings.HOST, settings.PORT)
    mcp.run(transport=transport)
