from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase24.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
os.environ["JOB_QUEUE_BACKEND"] = "database"
os.environ["DEBUG"] = "true"
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services.auth import DEV_ADMIN_EMAIL, DEV_ADMIN_PASSWORD  # noqa: E402


INITIAL_XML = "<mxGraphModel><root><mxCell id='0'/><mxCell id='1' parent='0'/></root></mxGraphModel>"
UPDATED_XML = (
    "<mxGraphModel><root><mxCell id='0'/><mxCell id='1' parent='0'/>"
    "<mxCell id='node-1' value='Saved node' parent='1' vertex='1'/></root></mxGraphModel>"
)


def main() -> int:
    with TestClient(app) as client:
        login = client.post("/api/auth/login", json={"email": DEV_ADMIN_EMAIL, "password": DEV_ADMIN_PASSWORD})
        token = login.json()["token"] if login.status_code == 200 else ""
        headers = {"Authorization": f"Bearer {token}"}

        created = client.post(
            "/api/diagrams",
            headers=headers,
            json={
                "title": "Drawio Save Flow",
                "objective": "Verify self-hosted draw.io save/load persistence.",
                "owner": "Diagram Test",
                "drawioXml": INITIAL_XML,
                "specJson": {"title": "Drawio Save Flow", "reviewStatus": "needs_review"},
            },
        )
        created_body = created.json() if created.status_code == 200 else {}

        loaded = client.get(f"/api/diagrams/{created_body.get('slug', '')}", headers=headers) if created_body else None
        loaded_body = loaded.json() if loaded and loaded.status_code == 200 else {}

        updated = (
            client.post(
                f"/api/diagrams/{created_body['id']}/update",
                headers=headers,
                json={
                    "title": created_body["title"],
                    "objective": created_body["objective"],
                    "owner": created_body["owner"],
                    "collectionId": created_body.get("collectionId"),
                    "actorLanes": created_body.get("actorLanes", []),
                    "sourcePageIds": created_body.get("sourcePageIds", []),
                    "sourceIds": created_body.get("sourceIds", []),
                    "entryPoints": created_body.get("entryPoints", []),
                    "exitPoints": created_body.get("exitPoints", []),
                    "relatedDiagramIds": created_body.get("relatedDiagramIds", []),
                    "specJson": {**(created_body.get("specJson") or {}), "editorSave": True},
                    "drawioXml": UPDATED_XML,
                    "changeSummary": "Persist draw.io XML from editor save",
                    "expectedVersion": created_body.get("currentVersion"),
                },
            )
            if created_body
            else None
        )
        updated_body = updated.json() if updated and updated.status_code == 200 else {}

        reloaded = client.get(f"/api/diagrams/{created_body.get('slug', '')}", headers=headers) if created_body else None
        reloaded_body = reloaded.json() if reloaded and reloaded.status_code == 200 else {}
        versions = client.get(f"/api/diagrams/{created_body.get('id', '')}/versions", headers=headers) if created_body else None
        versions_body = versions.json() if versions and versions.status_code == 200 else []
        audit = client.get(f"/api/diagrams/{created_body.get('id', '')}/audit", headers=headers) if created_body else None
        audit_body = audit.json() if audit and audit.status_code == 200 else []

    payload = {
        "success": True,
        "login": login.status_code,
        "created": created.status_code,
        "loaded": loaded.status_code if loaded else None,
        "updated": updated.status_code if updated else None,
        "reloaded": reloaded.status_code if reloaded else None,
        "versions": versions.status_code if versions else None,
        "audit": audit.status_code if audit else None,
        "initialXmlLoaded": loaded_body.get("drawioXml") == INITIAL_XML,
        "updatedXmlPersisted": reloaded_body.get("drawioXml") == UPDATED_XML,
        "currentVersion": reloaded_body.get("currentVersion"),
        "versionCount": len(versions_body),
        "lastChangeSummary": versions_body[0].get("changeSummary") if versions_body else None,
        "auditActions": [item.get("action") for item in audit_body],
    }

    checks = [
        payload["login"] == 200,
        payload["created"] == 200,
        payload["loaded"] == 200,
        payload["updated"] == 200,
        payload["reloaded"] == 200,
        payload["versions"] == 200,
        payload["audit"] == 200,
        payload["initialXmlLoaded"],
        payload["updatedXmlPersisted"],
        payload["currentVersion"] == 2,
        payload["versionCount"] >= 2,
        payload["lastChangeSummary"] == "Persist draw.io XML from editor save",
        "diagram_updated" in payload["auditActions"],
    ]
    if not all(checks):
        payload["success"] = False
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
