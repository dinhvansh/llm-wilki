from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase25.db"
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


def _find_first(items: list[dict]) -> dict | None:
    return items[0] if items else None


def main() -> int:
    with TestClient(app) as client:
        login = client.post("/api/auth/login", json={"email": DEV_ADMIN_EMAIL, "password": DEV_ADMIN_PASSWORD})
        token = login.json()["token"] if login.status_code == 200 else ""
        headers = {"Authorization": f"Bearer {token}"}

        pages = client.get("/api/pages?pageSize=5", headers=headers)
        sources = client.get("/api/sources?pageSize=5", headers=headers)
        page = _find_first((pages.json() if pages.status_code == 200 else {}).get("data", []))
        source = _find_first((sources.json() if sources.status_code == 200 else {}).get("data", []))

        page_generation = (
            client.post(f"/api/diagrams/from-page/{page['id']}", headers=headers, json={"title": f"{page['title']} BPM Flow"})
            if page
            else None
        )
        source_generation = (
            client.post(f"/api/diagrams/from-source/{source['id']}", headers=headers, json={"title": f"{source['title']} BPM Flow"})
            if source
            else None
        )

    page_body = page_generation.json() if page_generation and page_generation.status_code == 200 else {}
    source_body = source_generation.json() if source_generation and source_generation.status_code == 200 else {}
    page_spec = page_body.get("specJson") or {}
    source_spec = source_body.get("specJson") or {}
    page_validation = page_spec.get("validation") or {}
    source_validation = source_spec.get("validation") or {}

    payload = {
        "success": True,
        "login": login.status_code,
        "pageList": pages.status_code,
        "sourceList": sources.status_code,
        "pageGenerate": page_generation.status_code if page_generation else None,
        "sourceGenerate": source_generation.status_code if source_generation else None,
        "pageDiagramSlug": page_body.get("slug"),
        "sourceDiagramSlug": source_body.get("slug"),
        "pageActors": len(page_spec.get("actors", [])),
        "pageNodes": len(page_spec.get("nodes", [])),
        "pageEdges": len(page_spec.get("edges", [])),
        "pageOpenQuestions": len(page_spec.get("openQuestions", [])),
        "pageCitations": len(page_spec.get("citations", [])),
        "pageValidationWarnings": len(page_validation.get("warnings", [])),
        "sourceActors": len(source_spec.get("actors", [])),
        "sourceNodes": len(source_spec.get("nodes", [])),
        "sourceEdges": len(source_spec.get("edges", [])),
        "sourceOpenQuestions": len(source_spec.get("openQuestions", [])),
        "sourceCitations": len(source_spec.get("citations", [])),
        "sourceValidationWarnings": len(source_validation.get("warnings", [])),
        "pageDrawioXml": "mxGraphModel" in str(page_body.get("drawioXml", "")),
        "sourceDrawioXml": "mxGraphModel" in str(source_body.get("drawioXml", "")),
    }

    checks = [
        payload["login"] == 200,
        payload["pageList"] == 200,
        payload["sourceList"] == 200,
        page is not None,
        source is not None,
        payload["pageGenerate"] == 200,
        payload["sourceGenerate"] == 200,
        bool(payload["pageDiagramSlug"]),
        bool(payload["sourceDiagramSlug"]),
        payload["pageActors"] >= 1,
        payload["pageNodes"] >= 3,
        payload["pageEdges"] >= 2,
        payload["pageOpenQuestions"] >= 1,
        payload["pageCitations"] >= 1,
        payload["pageDrawioXml"] is True,
        payload["sourceActors"] >= 1,
        payload["sourceNodes"] >= 3,
        payload["sourceEdges"] >= 2,
        payload["sourceOpenQuestions"] >= 1,
        payload["sourceCitations"] >= 1,
        payload["sourceDrawioXml"] is True,
    ]
    if not all(checks):
        payload["success"] = False
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
