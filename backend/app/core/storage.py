from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.config import settings
from app.core.ingest import ensure_upload_dir


class StorageError(RuntimeError):
    pass


def storage_config() -> dict:
    return {
        "backend": settings.STORAGE_BACKEND,
        "uploadDir": settings.UPLOAD_DIR,
        "s3EndpointUrl": settings.S3_ENDPOINT_URL,
        "s3Bucket": settings.S3_BUCKET,
        "s3Region": settings.S3_REGION,
    }


def save_source_bytes(filename: str, file_bytes: bytes) -> Path:
    if settings.STORAGE_BACKEND != "local":
        raise StorageError("Only local storage is active in this build; configure local upload storage or add an S3 client adapter.")
    upload_dir = ensure_upload_dir()
    safe_name = filename.replace("\\", "-").replace("/", "-")
    stored_path = upload_dir / f"{uuid4().hex[:8]}-{safe_name}"
    stored_path.write_bytes(file_bytes)
    return stored_path


def replace_source_bytes(path: str, file_bytes: bytes) -> Path:
    if settings.STORAGE_BACKEND != "local":
        raise StorageError("Only local storage refresh is active in this build.")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(file_bytes)
    return target
