from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from uuid import uuid4

from app.config import settings
from app.core.ingest import ensure_upload_dir


class StorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredObjectResult:
    backend: str
    bucket: str | None
    object_key: str
    local_path: Path
    checksum_sha256: str
    byte_size: int
    content_type: str | None
    metadata: dict


def storage_config() -> dict:
    return {
        "backend": settings.STORAGE_BACKEND,
        "uploadDir": settings.UPLOAD_DIR,
        "s3EndpointUrl": settings.S3_ENDPOINT_URL,
        "s3Bucket": settings.S3_BUCKET,
        "s3Region": settings.S3_REGION,
    }


def _safe_filename(filename: str) -> str:
    return filename.replace("\\", "-").replace("/", "-").strip() or "upload.bin"


def _local_upload_path(filename: str, object_id: str | None = None) -> Path:
    upload_dir = ensure_upload_dir()
    return upload_dir / f"{object_id or uuid4().hex[:8]}-{_safe_filename(filename)}"


def _object_key(filename: str, checksum: str, object_id: str) -> str:
    today = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    return f"sources/{today}/{checksum[:16]}-{object_id}-{_safe_filename(filename)}"


def _s3_client():
    try:
        import boto3
    except ImportError as exc:
        raise StorageError("STORAGE_BACKEND=s3 requires boto3 in backend requirements.") from exc
    if not settings.S3_BUCKET:
        raise StorageError("S3_BUCKET is required when STORAGE_BACKEND=s3.")
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL or None,
        region_name=settings.S3_REGION,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or None,
    )


def ensure_s3_bucket() -> None:
    if settings.STORAGE_BACKEND != "s3":
        return
    client = _s3_client()
    try:
        client.head_bucket(Bucket=settings.S3_BUCKET)
    except Exception:
        create_kwargs = {"Bucket": settings.S3_BUCKET}
        if settings.S3_REGION and settings.S3_REGION != "us-east-1":
            create_kwargs["CreateBucketConfiguration"] = {"LocationConstraint": settings.S3_REGION}
        client.create_bucket(**create_kwargs)


def save_source_object(filename: str, file_bytes: bytes, content_type: str | None = None) -> StoredObjectResult:
    checksum = hashlib.sha256(file_bytes).hexdigest()
    object_id = uuid4().hex[:8]
    object_key = _object_key(filename, checksum, object_id)
    local_path = _local_upload_path(filename, object_id=object_id)
    local_path.write_bytes(file_bytes)
    metadata = {"localCachePath": str(local_path)}

    if settings.STORAGE_BACKEND == "local":
        return StoredObjectResult(
            backend="local",
            bucket=None,
            object_key=str(local_path),
            local_path=local_path,
            checksum_sha256=checksum,
            byte_size=len(file_bytes),
            content_type=content_type,
            metadata=metadata,
        )

    if settings.STORAGE_BACKEND == "s3":
        ensure_s3_bucket()
        client = _s3_client()
        extra_args = {"ContentType": content_type} if content_type else {}
        client.put_object(Bucket=settings.S3_BUCKET, Key=object_key, Body=file_bytes, **extra_args)
        return StoredObjectResult(
            backend="s3",
            bucket=settings.S3_BUCKET,
            object_key=object_key,
            local_path=local_path,
            checksum_sha256=checksum,
            byte_size=len(file_bytes),
            content_type=content_type,
            metadata={**metadata, "endpointUrl": settings.S3_ENDPOINT_URL, "region": settings.S3_REGION},
        )

    raise StorageError(f"Unsupported STORAGE_BACKEND={settings.STORAGE_BACKEND!r}.")


def save_existing_file_object(path: Path, content_type: str | None = None) -> StoredObjectResult:
    if not path.exists() or not path.is_file():
        raise StorageError(f"Cannot store missing file: {path}")
    return save_source_object(path.name, path.read_bytes(), content_type=content_type)


def save_source_bytes(filename: str, file_bytes: bytes) -> Path:
    return save_source_object(filename, file_bytes).local_path


def replace_source_bytes(path: str, file_bytes: bytes) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(file_bytes)
    return target


def refresh_object_bytes(object_key: str, local_path: str | None, file_bytes: bytes, content_type: str | None = None) -> Path:
    target = replace_source_bytes(local_path or object_key, file_bytes)
    if settings.STORAGE_BACKEND == "s3":
        client = _s3_client()
        extra_args = {"ContentType": content_type} if content_type else {}
        client.put_object(Bucket=settings.S3_BUCKET, Key=object_key, Body=file_bytes, **extra_args)
    return target


def read_object_bytes(backend: str, object_key: str, local_path: str | None = None, bucket: str | None = None) -> bytes:
    if backend == "local":
        path = Path(local_path or object_key)
        if not path.exists():
            raise StorageError(f"Local storage object does not exist: {path}")
        return path.read_bytes()
    if backend == "s3":
        client = _s3_client()
        response = client.get_object(Bucket=bucket or settings.S3_BUCKET, Key=object_key)
        return response["Body"].read()
    raise StorageError(f"Unsupported storage backend={backend!r}.")
