from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase23.db"
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


def main() -> int:
    with TestClient(app) as client:
        login = client.post("/api/auth/login", json={"email": DEV_ADMIN_EMAIL, "password": DEV_ADMIN_PASSWORD})
        token = login.json()["token"] if login.status_code == 200 else ""
        headers = {"Authorization": f"Bearer {token}"}

        create_payload = {
            "title": "Phase 23 Review Workflow",
            "objective": "Validate BPM diagram CRUD and versioning.",
            "owner": "Phase23",
            "collectionId": "col-003",
            "actorLanes": ["Editor", "Reviewer", "System"],
            "sourcePageIds": ["page-004"],
            "sourceIds": ["src-003"],
            "entryPoints": ["Draft ready"],
            "exitPoints": ["Published", "Rejected"],
            "specJson": {
                "title": "Phase 23 Review Workflow",
                "actors": [{"id": "editor", "label": "Editor"}],
                "nodes": [{"id": "start", "type": "start", "label": "Draft ready", "owner": "editor"}],
                "edges": [],
            },
            "drawioXml": "<mxGraphModel><root /></mxGraphModel>",
        }
        created = client.post("/api/diagrams", headers=headers, json=create_payload)
        created_body = created.json() if created.status_code == 200 else {}
        diagram_id = created_body.get("id")
        diagram_slug = created_body.get("slug")

        listed = client.get("/api/diagrams?search=Phase%2023", headers=headers)
        fetched = client.get(f"/api/diagrams/{diagram_slug}", headers=headers) if diagram_slug else None
        updated = (
            client.post(
                f"/api/diagrams/{diagram_id}/update",
                headers=headers,
                json={
                    **create_payload,
                    "title": "Phase 23 Review Workflow Updated",
                    "changeSummary": "Add reviewer decision branch",
                    "expectedVersion": 1,
                    "specJson": {
                        "title": "Phase 23 Review Workflow Updated",
                        "actors": [{"id": "editor", "label": "Editor"}, {"id": "reviewer", "label": "Reviewer"}],
                        "nodes": [
                            {"id": "start", "type": "start", "label": "Draft ready", "owner": "editor"},
                            {"id": "decision", "type": "decision", "label": "Reviewer approve?", "owner": "reviewer"},
                        ],
                        "edges": [{"from": "start", "to": "decision"}],
                    },
                },
            )
            if diagram_id
            else None
        )
        versions = client.get(f"/api/diagrams/{diagram_id}/versions", headers=headers) if diagram_id else None
        published = client.post(f"/api/diagrams/{diagram_id}/publish", headers=headers) if diagram_id else None
        unpublished = client.post(f"/api/diagrams/{diagram_id}/unpublish", headers=headers) if diagram_id else None
        audit = client.get(f"/api/diagrams/{diagram_id}/audit", headers=headers) if diagram_id else None

    payload = {
        "success": True,
        "login": login.status_code,
        "create": created.status_code,
        "diagramSlug": diagram_slug,
        "list": listed.status_code,
        "listCount": listed.json().get("total") if listed.status_code == 200 else None,
        "get": fetched.status_code if fetched else None,
        "update": updated.status_code if updated else None,
        "updatedVersion": updated.json().get("currentVersion") if updated and updated.status_code == 200 else None,
        "versions": versions.status_code if versions else None,
        "versionCount": len(versions.json()) if versions and versions.status_code == 200 else None,
        "publish": published.status_code if published else None,
        "publishStatus": published.json().get("status") if published and published.status_code == 200 else None,
        "unpublish": unpublished.status_code if unpublished else None,
        "unpublishStatus": unpublished.json().get("status") if unpublished and unpublished.status_code == 200 else None,
        "audit": audit.status_code if audit else None,
        "auditActions": [item.get("action") for item in (audit.json() if audit and audit.status_code == 200 else [])],
    }
    checks = [
        payload["login"] == 200,
        payload["create"] == 200,
        bool(payload["diagramSlug"]),
        payload["list"] == 200,
        (payload["listCount"] or 0) >= 1,
        payload["get"] == 200,
        payload["update"] == 200,
        payload["updatedVersion"] == 2,
        payload["versions"] == 200,
        (payload["versionCount"] or 0) >= 2,
        payload["publish"] == 200,
        payload["publishStatus"] == "published",
        payload["unpublish"] == 200,
        payload["unpublishStatus"] == "draft",
        payload["audit"] == 200,
        {"diagram_created", "diagram_updated", "diagram_published", "diagram_unpublished"}.issubset(set(payload["auditActions"] or [])),
    ]
    if not all(checks):
        payload["success"] = False
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
