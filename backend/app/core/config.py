from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "retail_db"
    POSTGRES_USER: str = "retail_user"
    POSTGRES_PASSWORD: str = "secure_password"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Auth
    SECRET_KEY: str = "change_me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # External APIs
    YANDEX_GEOCODER_API_KEY: str = ""
    TWOGIS_API_KEY: str = ""
    OPENROUTESERVICE_API_KEY: str = ""
    OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # App
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Scoring model defaults
    HUFF_BETA: float = 2.0
    CANNIBALIZATION_RADIUS_M: int = 800
    ISOCHRONE_CACHE_TTL_DAYS: int = 7

    # ML platform
    ML_MODEL_DIR: str = "models"
    ML_MODEL_VERSION: str = "1.0"

    # AI Orchestrator (OpenRouter)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "qwen/qwen3.7-plus"
    OPENROUTER_TIMEOUT_S: int = 60
    AI_MAX_TOOL_ITERATIONS: int = 5

    # Events
    EVENT_STREAM_PREFIX: str = "events"
    EVENTS_ENABLED: bool = True

    # Observability
    METRICS_ENABLED: bool = True


settings = Settings()
