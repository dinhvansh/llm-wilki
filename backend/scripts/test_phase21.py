from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase21.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
os.environ["JOB_QUEUE_BACKEND"] = "database"
os.environ["DEBUG"] = "true"
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.services.audit import create_audit_log  # noqa: E402
from app.services.auth import DEV_ADMIN_EMAIL, DEV_ADMIN_PASSWORD  # noqa: E402
from app.services.jobs import create_job, update_job  # noqa: E402


def main() -> int:
    with TestClient(app) as client:
        login = client.post("/api/auth/login", json={"email": DEV_ADMIN_EMAIL, "password": DEV_ADMIN_PASSWORD})
        token = login.json()["token"] if login.status_code == 200 else ""
        headers = {"Authorization": f"Bearer {token}", "X-Request-ID": "phase21-request"}

        db = SessionLocal()
        try:
            failed = create_job(db, "ingest", "src-001", status="pending", actor="Phase21", max_attempts=3)
            update_job(db, failed.id, status="failed", error_message="Phase21 synthetic failure", finished=True)
            create_audit_log(db, action="phase21_audit", object_type="system", object_id="phase21", actor="Phase21", summary="Phase21 audit smoke")
            db.commit()
            failed_id = failed.id
        finally:
            db.close()

        health = client.get("/health", headers=headers)
        operations = client.get("/api/admin/operations", headers=headers)
        audit = client.get("/api/admin/audit?action=phase21_audit", headers=headers)
        export_config = client.get("/api/admin/config/export", headers=headers)
        import_config = client.post("/api/admin/config/import", headers=headers, json={"settings": {"searchResultLimit": 11}})
        bulk_retry = client.post("/api/admin/jobs/bulk-retry", headers=headers, json={"jobIds": [failed_id], "limit": 5})

    payload = {
        "success": True,
        "login": login.status_code,
        "requestId": health.headers.get("X-Request-ID"),
        "operations": operations.status_code,
        "failedMetric": operations.json().get("jobMetrics", {}).get("failed") if operations.status_code == 200 else None,
        "audit": audit.status_code,
        "auditCount": len(audit.json()) if audit.status_code == 200 else None,
        "export": export_config.status_code,
        "exportHasSettings": bool(export_config.json().get("settings")) if export_config.status_code == 200 else False,
        "import": import_config.status_code,
        "importSearchLimit": import_config.json().get("settings", {}).get("searchResultLimit") if import_config.status_code == 200 else None,
        "bulkRetry": bulk_retry.status_code,
        "retriedCount": bulk_retry.json().get("retriedCount") if bulk_retry.status_code == 200 else None,
    }
    checks = [
        payload["login"] == 200,
        payload["requestId"] == "phase21-request",
        payload["operations"] == 200,
        (payload["failedMetric"] or 0) >= 1,
        payload["audit"] == 200,
        payload["auditCount"] == 1,
        payload["export"] == 200,
        payload["exportHasSettings"],
        payload["import"] == 200,
        payload["importSearchLimit"] == 11,
        payload["bulkRetry"] == 200,
        payload["retriedCount"] == 1,
    ]
    if not all(checks):
        payload["success"] = False
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
