from app.core.config.settings import get_settings

settings = get_settings()

REDIS_URL = (
    f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
)
