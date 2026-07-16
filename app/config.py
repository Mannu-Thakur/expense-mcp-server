from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # Application
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # MCP Server
    MCP_SERVER_NAME: str = "Expense Tracker"
    HOST: str = "0.0.0.0"
    PORT: int = 8000  # Render sets this to 10000 via env var
    TRANSPORT: str = "stdio"  # "stdio" | "streamable-http"

    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/expenses.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()