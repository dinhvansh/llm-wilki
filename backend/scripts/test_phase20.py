from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase20.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
os.environ["JOB_QUEUE_BACKEND"] = "database"
os.environ["DEBUG"] = "true"
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.bootstrap import init_database  # noqa: E402
from app.core.storage import storage_config  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.services import sources as source_service  # noqa: E402
from app.services.auth import DEV_ADMIN_EMAIL, DEV_ADMIN_PASSWORD  # noqa: E402


def main() -> int:
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)
        first, first_path = source_service.create_text_source_record(
            db,
            title="Phase20 Duplicate One",
            content="This repeated body validates source checksum dedupe metadata for connector portability.",
            actor="Phase20",
        )
        second, _ = source_service.create_text_source_record(
            db,
            title="Phase20 Duplicate Two",
            content="This repeated body validates source checksum dedupe metadata for connector portability.",
            actor="Phase20",
        )

        original_fetch = source_service.fetch_url_content
        source_service.fetch_url_content = lambda url: (  # type: ignore[assignment]
            "Phase20 URL",
            b"Refreshed URL source content with enough readable text for connector tests.",
            "text/plain",
            {
                "inputConnector": "url",
                "sourceKind": "web",
                "fetchedUrl": url,
                "contentType": "text/plain",
                "connector": {"id": "url", "supportsRefresh": True},
                "validation": {"maxBytes": source_service.MAX_CONNECTOR_BYTES},
            },
        )
        try:
            url_source, _ = source_service.create_url_source_record(db, url="https://example.test/phase20", title="Phase20 URL", actor="Phase20")
            refreshed = source_service.refresh_url_source_record(db, url_source.id, actor="Phase20")
        finally:
            source_service.fetch_url_content = original_fetch  # type: ignore[assignment]

        payload = {
            "success": True,
            "registryIds": [item["id"] for item in source_service.get_connector_registry()],
            "storageBackend": storage_config()["backend"],
            "checksumStable": first.checksum == second.checksum,
            "duplicateOf": (second.metadata_json or {}).get("dedupe", {}).get("duplicateOfSourceId"),
            "fileStored": first_path.exists(),
            "urlRefreshStatus": refreshed.parse_status if refreshed else None,
            "urlRefreshedBy": (refreshed.metadata_json or {}).get("refreshedBy") if refreshed else None,
        }
    finally:
        db.close()

    source_service.fetch_url_content = lambda url: (  # type: ignore[assignment]
        "Phase20 URL",
        b"Endpoint refreshed URL source content with enough readable text for connector tests.",
        "text/plain",
        {
            "inputConnector": "url",
            "sourceKind": "web",
            "fetchedUrl": url,
            "contentType": "text/plain",
            "connector": {"id": "url", "supportsRefresh": True},
            "validation": {"maxBytes": source_service.MAX_CONNECTOR_BYTES},
        },
    )
    with TestClient(app) as client:
        login = client.post("/api/auth/login", json={"email": DEV_ADMIN_EMAIL, "password": DEV_ADMIN_PASSWORD})
        token = login.json()["token"] if login.status_code == 200 else ""
        headers = {"Authorization": f"Bearer {token}"}
        connectors = client.get("/api/sources/connectors")
        refresh = client.post(f"/api/sources/{url_source.id}/refresh", headers=headers)
        payload.update(
            {
                "connectorsEndpoint": connectors.status_code,
                "connectorCount": len(connectors.json()) if connectors.status_code == 200 else 0,
                "refreshEndpoint": refresh.status_code,
            }
        )
    source_service.fetch_url_content = original_fetch  # type: ignore[assignment]

    checks = [
        {"file", "url", "txt", "transcript", "image_ocr"}.issubset(set(payload["registryIds"])),
        payload["storageBackend"] == "local",
        payload["checksumStable"],
        payload["duplicateOf"] == first.id,
        payload["fileStored"],
        payload["urlRefreshStatus"] == "parsing",
        payload["urlRefreshedBy"] == "Phase20",
        payload["connectorsEndpoint"] == 200,
        payload["connectorCount"] >= 5,
        payload["refreshEndpoint"] in {200, 400, 404},
    ]
    if not all(checks):
        payload["success"] = False
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
