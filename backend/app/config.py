"""EduScale Application Configuration."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "EduScale"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql://eduscale:eduscale_pass@localhost:5432/eduscale"
    DATABASE_ECHO: bool = False

    # Authentication
    SECRET_KEY: str = "dev-secret-key-change-in-production-at-least-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_RELOAD: bool = True
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ML Models
    MODEL_DIR: str = "ml/artifacts"
    DEMO_MODE: bool = True

    # Cloud (optional)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"

    # AI Provider (optional)
    AI_NOTES_PROVIDER: str = "none"

    # Experiments
    EXPERIMENT_MAX_DURATION_SECONDS: int = 3600
    WORKLOAD_SIM_DEFAULT_SEED: int = 42

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
