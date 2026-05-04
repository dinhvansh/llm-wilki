from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase27.db"
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

        procedural_page = client.get("/api/diagrams/assess-page/page-004", headers=headers)
        reference_page = client.get("/api/diagrams/assess-page/page-001", headers=headers)
        workflow_source = client.get("/api/diagrams/assess-source/src-003", headers=headers)
        policy_source = client.get("/api/diagrams/assess-source/src-001", headers=headers)

    procedural_body = procedural_page.json() if procedural_page.status_code == 200 else {}
    reference_body = reference_page.json() if reference_page.status_code == 200 else {}
    workflow_source_body = workflow_source.json() if workflow_source.status_code == 200 else {}
    policy_source_body = policy_source.json() if policy_source.status_code == 200 else {}

    payload = {
        "success": True,
        "login": login.status_code,
        "proceduralPage": procedural_page.status_code,
        "referencePage": reference_page.status_code,
        "workflowSource": workflow_source.status_code,
        "policySource": policy_source.status_code,
        "proceduralClassification": procedural_body.get("classification"),
        "referenceClassification": reference_body.get("classification"),
        "workflowSourceClassification": workflow_source_body.get("classification"),
        "policySourceClassification": policy_source_body.get("classification"),
        "proceduralScore": procedural_body.get("score"),
        "referenceScore": reference_body.get("score"),
    }

    checks = [
        payload["login"] == 200,
        payload["proceduralPage"] == 200,
        payload["referencePage"] == 200,
        payload["workflowSource"] == 200,
        payload["policySource"] == 200,
        payload["proceduralClassification"] in {"recommended", "optional"},
        payload["referenceClassification"] == "not_recommended",
        payload["workflowSourceClassification"] in {"recommended", "optional"},
        payload["policySourceClassification"] == "not_recommended",
        float(payload["proceduralScore"] or 0) > float(payload["referenceScore"] or 0),
    ]
    if not all(checks):
        payload["success"] = False
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
