from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # General
    app_name: str = "SantoniBot"
    app_env: str = "development"
    debug: bool = True

    # Backend
    backend_port: int = 8000
    secret_key: str = "change-this-to-a-random-secret-key-min-32-chars"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 480

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
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-70b-versatile"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250929"

    # ChromaDB
    chroma_host: str = "chromadb"
    chroma_port: int = 8001

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def idempiere_database_url(self) -> str:
        return (
            f"postgresql://{self.idempiere_db_user}:{self.idempiere_db_password}"
            f"@{self.idempiere_db_host}:{self.idempiere_db_port}/{self.idempiere_db_name}"
        )

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
