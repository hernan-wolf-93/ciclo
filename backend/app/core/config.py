from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Lee la configuración desde variables de entorno o desde backend/.env."""

    database_url: str
    secret_key: str = Field(min_length=32)
    access_token_expire_minutes: int = 480
    test_database_url: str | None = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def origenes_cors(self) -> list[str]:
        """Orígenes permitidos por CORS, a partir de CORS_ORIGINS (separados por coma)."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

settings = Settings()