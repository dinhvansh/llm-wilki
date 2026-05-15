from __future__ import annotations

import redis
from sqlalchemy import text

from app.config import settings
from app.db.database import SessionLocal


def validate_startup_config() -> dict:
    warnings: list[str] = []
    errors: list[str] = []
    if not settings.DATABASE_URL:
        errors.append("DATABASE_URL is required")
    if settings.JOB_QUEUE_BACKEND == "redis" and not settings.REDIS_URL:
        errors.append("REDIS_URL is required when JOB_QUEUE_BACKEND=redis")
    if not settings.DEBUG and settings.SECRET_KEY == "changeme-in-production":
        errors.append("SECRET_KEY must be changed when DEBUG=false")
    if not settings.DEBUG and not settings.RUNTIME_SECRET_ENCRYPTION_KEY:
        warnings.append("RUNTIME_SECRET_ENCRYPTION_KEY should be set when DEBUG=false")
    if settings.LLM_PROVIDER != "none" and not settings.LLM_MODEL:
        warnings.append("LLM_PROVIDER is enabled but LLM_MODEL is empty")
    return {"ok": not errors, "warnings": warnings, "errors": errors}


def check_database() -> dict:
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def check_redis() -> dict:
    if settings.JOB_QUEUE_BACKEND != "redis":
        return {"ok": True, "skipped": True, "reason": "JOB_QUEUE_BACKEND is not redis"}
    try:
        client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
        client.ping()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def readiness_payload() -> dict:
    config = validate_startup_config()
    database = check_database()
    redis_status = check_redis()
    ok = bool(config["ok"] and database["ok"] and redis_status["ok"])
    return {
        "status": "ready" if ok else "not_ready",
        "ok": ok,
        "checks": {
            "config": config,
            "database": database,
            "redis": redis_status,
        },
    }
