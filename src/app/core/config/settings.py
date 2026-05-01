from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: str = Field(pattern=r"^(test|dev|ppr|prod)$")

    APP_NAME: str = Field(min_length=3, max_length=20)
    APP_VERSION: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    APP_DESCRIPTION: str = Field(min_length=3, max_length=200)
    APP_PORT: int = Field(ge=1, le=65535)

    CORS_ORIGINS: list[str] = Field(default=["*"])

    LOG_LEVEL: str = Field(pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    LOG_MAX_BYTES: int
    LOG_BACKUP_COUNT: int

    DB_HOST: str = Field(min_length=2, max_length=50)
    DB_PORT: int = Field(ge=1, le=65535)
    DB_NAME: str = Field(min_length=2, max_length=50)
    DB_USER: str = Field(min_length=2, max_length=50)
    DB_PASSWORD: str = Field(min_length=8, max_length=128)

    REDIS_HOST: str = Field(min_length=2, max_length=50)
    REDIS_PORT: int = Field(ge=1, le=65535)
    REDIS_PASSWORD: str = Field(min_length=8, max_length=128)

    API_KEY: str = Field(min_length=32)

    JWT_SECRET_KEY: str = Field()
    JWT_ALGORITHM: str = Field(pattern=r"^(HS256|RS256)$")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(le=60)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(le=45)
    JWT_SESSION_MAX_LIFETIME_DAYS: int = Field(le=100)
    JWT_SESSION_MAX_COUNT: int = Field(le=10)

    LLM_TIMEOUT_SECONDS: int = Field(ge=10, le=300)

    REVIEW_MIN_MESSAGES: int = Field(ge=1, le=100)
    REVIEW_TOP_WORST_CATEGORIES: int = Field(ge=1, le=9)
    REVIEW_WORST_MESSAGES_PER_CATEGORY: int = Field(ge=1, le=20)

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",  # silently ignore infra-only vars (DOCKER_IMAGE, CADDY_*, etc.)
    )
    
    
@lru_cache
def get_settings() -> Settings:
    """Load and cache settings"""
    return Settings()
