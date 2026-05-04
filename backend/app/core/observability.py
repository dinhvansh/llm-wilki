from __future__ import annotations

import json
import logging
import time
from collections import Counter
from datetime import timezone
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
        }
        for key in ["request_id", "method", "path", "status_code", "duration_ms"]:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False)


def configure_structured_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    root = logging.getLogger()
    if not any(isinstance(existing.formatter, JsonLogFormatter) for existing in root.handlers):
        root.handlers = [handler]
    root.setLevel(logging.INFO)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or f"req-{uuid4().hex[:12]}"
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - started) * 1000)
        response.headers["X-Request-ID"] = request_id
        logging.getLogger("app.request").info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


def duration_ms(started_at, finished_at) -> int | None:
    if not started_at or not finished_at:
        return None
    left = started_at if started_at.tzinfo else started_at.replace(tzinfo=timezone.utc)
    right = finished_at if finished_at.tzinfo else finished_at.replace(tzinfo=timezone.utc)
    return max(0, int((right - left).total_seconds() * 1000))


def percentile(values: list[int], pct: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((pct / 100) * (len(ordered) - 1)))))
    return ordered[index]


def summarize_status(rows, attr: str = "status") -> dict:
    return dict(Counter(getattr(row, attr) for row in rows))
