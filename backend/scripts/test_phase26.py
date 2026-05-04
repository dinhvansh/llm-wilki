from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase26.db"
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


def _first(items: list[dict]) -> dict | None:
    return items[0] if items else None


def main() -> int:
    with TestClient(app) as client:
        login = client.post("/api/auth/login", json={"email": DEV_ADMIN_EMAIL, "password": DEV_ADMIN_PASSWORD})
        token = login.json()["token"] if login.status_code == 200 else ""
        headers = {"Authorization": f"Bearer {token}"}

        pages = client.get("/api/pages?pageSize=2", headers=headers).json().get("data", [])
        sources = client.get("/api/sources?pageSize=2", headers=headers).json().get("data", [])
        page = _first(pages)
        source = _first(sources)

        first = client.post(f"/api/diagrams/from-page/{page['id']}", headers=headers, json={"title": "Traceability Flow A"}) if page else None
        second = client.post(f"/api/diagrams/from-source/{source['id']}", headers=headers, json={"title": "Traceability Flow B"}) if source else None
        first_body = first.json() if first and first.status_code == 200 else {}
        second_body = second.json() if second and second.status_code == 200 else {}

        linked = (
            client.post(
                f"/api/diagrams/{first_body['id']}/update",
                headers=headers,
                json={
                    "title": first_body["title"],
                    "objective": first_body["objective"],
                    "owner": first_body["owner"],
                    "collectionId": first_body.get("collectionId"),
                    "actorLanes": first_body.get("actorLanes", []),
                    "sourcePageIds": first_body.get("sourcePageIds", []),
                    "sourceIds": first_body.get("sourceIds", []),
                    "entryPoints": first_body.get("entryPoints", []),
                    "exitPoints": first_body.get("exitPoints", []),
                    "relatedDiagramIds": [second_body["id"]],
                    "specJson": first_body.get("specJson", {}),
                    "drawioXml": first_body.get("drawioXml", ""),
                    "changeSummary": "Link related flow",
                    "expectedVersion": first_body.get("currentVersion"),
                },
            )
            if first_body and second_body
            else None
        )

        submit_review = client.post(f"/api/diagrams/{first_body['id']}/submit-review", headers=headers) if first_body else None
        approve_review = (
            client.post(f"/api/diagrams/{first_body['id']}/approve-review", headers=headers, json={"comment": "Looks traceable."})
            if first_body
            else None
        )
        list_by_page = client.get(f"/api/diagrams?pageId={page['id']}", headers=headers) if page else None
        list_by_source = client.get(f"/api/diagrams?sourceId={source['id']}", headers=headers) if source else None
        detail = client.get(f"/api/diagrams/{first_body['slug']}", headers=headers) if first_body else None

    linked_body = linked.json() if linked and linked.status_code == 200 else {}
    detail_body = detail.json() if detail and detail.status_code == 200 else {}
    spec = detail_body.get("specJson") or {}

    payload = {
        "success": True,
        "login": login.status_code,
        "firstGenerate": first.status_code if first else None,
        "secondGenerate": second.status_code if second else None,
        "linkUpdate": linked.status_code if linked else None,
        "submitReview": submit_review.status_code if submit_review else None,
        "approveReview": approve_review.status_code if approve_review else None,
        "listByPage": list_by_page.status_code if list_by_page else None,
        "listBySource": list_by_source.status_code if list_by_source else None,
        "detail": detail.status_code if detail else None,
        "relatedDiagramCount": len(detail_body.get("relatedDiagrams", [])),
        "linkedPageCount": len(detail_body.get("linkedPages", [])),
        "linkedSourceCount": len(detail_body.get("linkedSources", [])),
        "reviewStatus": spec.get("reviewStatus"),
        "nodeCitations": len(spec.get("nodeCitations", [])),
        "edgeCitations": len(spec.get("edgeCitations", [])),
        "pageFilterCount": len((list_by_page.json() if list_by_page and list_by_page.status_code == 200 else {}).get("data", [])),
        "sourceFilterCount": len((list_by_source.json() if list_by_source and list_by_source.status_code == 200 else {}).get("data", [])),
    }

    checks = [
        payload["login"] == 200,
        payload["firstGenerate"] == 200,
        payload["secondGenerate"] == 200,
        payload["linkUpdate"] == 200,
        payload["submitReview"] == 200,
        payload["approveReview"] == 200,
        payload["listByPage"] == 200,
        payload["listBySource"] == 200,
        payload["detail"] == 200,
        payload["relatedDiagramCount"] >= 1,
        payload["linkedPageCount"] >= 1,
        payload["linkedSourceCount"] >= 1,
        payload["reviewStatus"] == "approved",
        payload["nodeCitations"] >= 1,
        payload["edgeCitations"] >= 1,
        payload["pageFilterCount"] >= 1,
        payload["sourceFilterCount"] >= 1,
    ]
    if not all(checks):
        payload["success"] = False
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
