from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables or a .env file."""

    app_name: str = "SpendSmart"
    secret_key: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, gt=0)
    database_url: str = "sqlite:///./data/spendsmart.db"
    login_max_attempts: int = Field(default=5, gt=0)
    login_window_seconds: int = Field(default=900, gt=0)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_secret_key(self) -> "Settings":
        """Reject empty or placeholder secrets."""
        secret = self.secret_key.get_secret_value().strip()

        if not secret or secret == "replace-with-a-strong-random-secret":
            raise ValueError("SECRET_KEY must be set to a non-placeholder secret")

        if len(secret) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")

        if self.algorithm != "HS256":
            raise ValueError("Only HS256 is supported for JWT signing")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
