import logging
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings
from pydantic import model_validator
from functools import lru_cache

_config_logger = logging.getLogger("santonibot.config")


class Settings(BaseSettings):
    # General
    app_name: str = "SantoniBot"
    app_env: str = "development"
    debug: bool = False
    domain: str = "localhost"

    # Backend
    backend_port: int = 8000
    secret_key: str = "change-this-to-a-random-secret-key-min-32-chars"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 30

    # Sentry (optional - leave empty to disable)
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.2
    sentry_profiles_sample_rate: float = 0.1

    # Internal Database
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "santonibot"
    postgres_user: str = "santonibot"
    postgres_password: str = "changeme"

    # iDempiere Database (read-only)
    idempiere_db_host: str = "192.168.1.73"
    idempiere_db_port: int = 5432
    idempiere_db_name: str = "idempiere_produccion"
    idempiere_db_user: str = "ova"
    idempiere_db_password: str = ""

    # AI Providers
    # ai_provider: "openrouter" (recommended), "groq" (free but limited), or "anthropic" (Claude)
    ai_provider: str = "openrouter"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    openrouter_api_key: str = ""
    openrouter_model: str = "deepseek/deepseek-chat-v3-0324"
    openrouter_provider: str = ""  # Force specific provider (e.g., "NovitaAI")
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    anthropic_base_url: str = ""  # Proxy URL for Claude API (e.g., Cloudflare Worker)

    # ChromaDB
    chroma_host: str = "chromadb"
    chroma_port: int = 8000

    # Historical data: queries before this date use local DB instead of iDempiere
    # Values: "today" (recommended) = only today goes to iDempiere, everything else local
    #         "YYYY-MM-DD" = fixed cutoff date
    historical_data_cutoff: str = "today"
    historical_data_enabled: bool = False  # Enable after running extract_historical_data.py

    # Access control
    enforce_business_hours: bool = False  # Set True to restrict to business hours
    business_hours_start: int = 6   # 6 AM Venezuela
    business_hours_end: int = 21    # 9 PM Venezuela
    allowed_networks: str = ""      # Comma-separated CIDRs, e.g. "192.168.1.0/24,10.0.0.0/8"

    @model_validator(mode="after")
    def _check_secret_key(self):
        default = "change-this-to-a-random-secret-key-min-32-chars"
        if self.secret_key == default and self.app_env == "production":
            raise ValueError(
                "SECRET_KEY no puede ser el valor por defecto en producción. "
                'Genere una clave segura con: python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )
        if len(self.secret_key) < 32:
            _config_logger.warning(
                "SECRET_KEY tiene menos de 32 caracteres. "
                "Se recomienda mínimo 64 caracteres aleatorios para producción."
            )
        return self

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{quote_plus(self.postgres_password)}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def idempiere_database_url(self) -> str:
        return (
            f"postgresql://{self.idempiere_db_user}:{quote_plus(self.idempiere_db_password)}"
            f"@{self.idempiere_db_host}:{self.idempiere_db_port}/{self.idempiere_db_name}"
        )

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
