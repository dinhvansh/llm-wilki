from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ConnectorCapability:
    id: str
    label: str
    source_type: str
    supports_rebuild: bool
    supports_refresh: bool
    max_size_bytes: int
    auth_required: bool = False
    error_taxonomy: tuple[str, ...] = ("validation_error", "fetch_error", "parse_error", "storage_error")


CONNECTORS: dict[str, ConnectorCapability] = {
    "file": ConnectorCapability("file", "File Upload", "file", True, False, 25 * 1024 * 1024),
    "url": ConnectorCapability("url", "Web URL", "url", True, True, 2 * 1024 * 1024),
    "txt": ConnectorCapability("txt", "Text Paste", "txt", True, False, 1024 * 1024),
    "transcript": ConnectorCapability("transcript", "Transcript", "transcript", True, False, 1024 * 1024),
    "image_ocr": ConnectorCapability("image_ocr", "Image OCR", "image_ocr", True, False, 25 * 1024 * 1024),
}


def list_connector_capabilities() -> list[dict]:
    return [asdict(capability) for capability in CONNECTORS.values()]


def get_connector_capability(connector_id: str) -> ConnectorCapability | None:
    return CONNECTORS.get(connector_id)


def connector_error(code: str, message: str, connector_id: str) -> dict:
    return {"connectorId": connector_id, "errorCode": code, "message": message}
