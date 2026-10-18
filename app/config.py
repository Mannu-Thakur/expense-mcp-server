from pathlib import Path
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    MCP_SERVER_NAME: str = "Expense Tracker"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    TRANSPORT: str = "stdio"

    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/expenses.db"

    OAUTH_ISSUER_URL: str | None = None
    OAUTH_JWKS_URL: str | None = None
    OAUTH_AUDIENCE: str | None = None
    OAUTH_RESOURCE_URL: str | None = None
    OAUTH_JWT_ALGORITHM: str = "RS256"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def oauth_config(self, *, required: bool = False) -> dict[str, str] | None:
        keys = {
            "OAUTH_ISSUER_URL": self.OAUTH_ISSUER_URL,
            "OAUTH_JWKS_URL": self.OAUTH_JWKS_URL,
            "OAUTH_AUDIENCE": self.OAUTH_AUDIENCE,
            "OAUTH_RESOURCE_URL": self.OAUTH_RESOURCE_URL,
        }
        configured = {key: value.strip() for key, value in keys.items() if value and value.strip()}
        if not configured:
            if required:
                raise ValueError(
                    "HTTP transport requires OAUTH_ISSUER_URL, OAUTH_JWKS_URL, "
                    "OAUTH_AUDIENCE, and OAUTH_RESOURCE_URL."
                )
            return None

        missing = [key for key, value in keys.items() if not value or not value.strip()]
        if missing:
            raise ValueError("Incomplete OAuth configuration; set: " + ", ".join(missing) + ".")

        algorithm = self.OAUTH_JWT_ALGORITHM.upper()
        allowed_algorithms = {"RS256", "RS384", "RS512", "ES256", "ES384"}
        if algorithm not in allowed_algorithms:
            raise ValueError("OAUTH_JWT_ALGORITHM must be a supported asymmetric JWT algorithm.")

        production = self.APP_ENV.lower() == "production"
        for key in ("OAUTH_ISSUER_URL", "OAUTH_JWKS_URL", "OAUTH_RESOURCE_URL"):
            value = configured[key]
            parsed = urlparse(value)
            try:
                parsed.port
            except ValueError as exc:
                raise ValueError(f"{key} must contain a valid port number.") from exc
            local_http = (
                not production
                and parsed.scheme == "http"
                and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
            )
            if parsed.scheme != "https" and not local_http:
                raise ValueError(f"{key} must use HTTPS except for loopback development URLs.")
            if not parsed.hostname or parsed.username or parsed.password:
                raise ValueError(f"{key} must be an absolute URL without embedded credentials.")
            if key == "OAUTH_ISSUER_URL" and (parsed.query or parsed.fragment):
                raise ValueError("OAUTH_ISSUER_URL must not contain a query string or fragment.")

        resource = urlparse(configured["OAUTH_RESOURCE_URL"])
        if resource.path != "/mcp" or resource.query or resource.fragment:
            raise ValueError("OAUTH_RESOURCE_URL must be the public MCP endpoint URL ending in /mcp.")

        return {
            "issuer_url": configured["OAUTH_ISSUER_URL"],
            "jwks_url": configured["OAUTH_JWKS_URL"],
            "audience": configured["OAUTH_AUDIENCE"],
            "resource_url": configured["OAUTH_RESOURCE_URL"],
            "algorithm": algorithm,
        }


settings = Settings()
