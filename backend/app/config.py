from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/llmwiki"
    REDIS_URL: str = "redis://localhost:6379/0"
    JOB_QUEUE_BACKEND: str = "redis"
    JOB_WORKER_POLL_SECONDS: float = 2.0
    JOB_MAX_ATTEMPTS: int = 3
    SECRET_KEY: str = "changeme-in-production"
    RUNTIME_SECRET_ENCRYPTION_KEY: str = ""
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    AUTO_SEED_DEMO_DATA: bool = True
    UPLOAD_DIR: str = "/app/data/uploads"
    STORAGE_BACKEND: str = "local"
    S3_ENDPOINT_URL: str = ""
    S3_BUCKET: str = ""
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    LLM_PROVIDER: str = "none"
    LLM_MODEL: str = ""
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "http://host.docker.internal:11434"
    LLM_TIMEOUT_SECONDS: int = 90
    DOCLING_OCR_ENGINE: str = "tesseract_cli"
    DOCLING_OCR_LANGS: List[str] = Field(default_factory=lambda: ["eng", "vie"])
    DOCLING_FORCE_FULL_PAGE_OCR: bool = True
    DOCLING_TESSERACT_CMD: str = "tesseract"
    DOCLING_TESSERACT_PSM: int | None = 6
    DOCLING_TESSDATA_PATH: str = "/usr/share/tesseract-ocr/5/tessdata"
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
            "http://localhost:3100",
            "http://127.0.0.1:3100",
        ]
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "yes", "on", "debug", "development"}:
                return True
            if lowered in {"0", "false", "no", "off", "release", "production"}:
                return False
        return bool(value)

    @field_validator("JOB_QUEUE_BACKEND")
    @classmethod
    def validate_job_queue_backend(cls, value):
        allowed = {"redis", "database"}
        lowered = str(value or "redis").strip().lower()
        if lowered not in allowed:
            raise ValueError(f"JOB_QUEUE_BACKEND must be one of {sorted(allowed)}")
        return lowered

    @field_validator("STORAGE_BACKEND")
    @classmethod
    def validate_storage_backend(cls, value):
        allowed = {"local", "s3"}
        lowered = str(value or "local").strip().lower()
        if lowered not in allowed:
            raise ValueError(f"STORAGE_BACKEND must be one of {sorted(allowed)}")
        return lowered

    @field_validator("DOCLING_OCR_ENGINE")
    @classmethod
    def validate_docling_ocr_engine(cls, value):
        allowed = {"tesseract_cli"}
        lowered = str(value or "tesseract_cli").strip().lower()
        if lowered not in allowed:
            raise ValueError(f"DOCLING_OCR_ENGINE must be one of {sorted(allowed)}")
        return lowered


settings = Settings()
