from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase15.db"
MIGRATION_DB_PATH = ROOT / "test_phase15_migration.db"
for path in [DB_PATH, MIGRATION_DB_PATH]:
    if path.exists():
        path.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
os.environ["JOB_QUEUE_BACKEND"] = "database"
os.environ["DEBUG"] = "true"
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.models import AuditLog, User  # noqa: E402
from app.services.auth import DEV_ADMIN_EMAIL, DEV_ADMIN_PASSWORD, hash_password  # noqa: E402


def run_migration_smoke() -> bool:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{MIGRATION_DB_PATH.as_posix()}"
    env["JOB_QUEUE_BACKEND"] = "database"
    env["DEBUG"] = "true"
    result = subprocess.run(
        [sys.executable, "-c", "from alembic.config import main; main()", "-c", "alembic.ini", "upgrade", "head"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=120,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        return False
    return MIGRATION_DB_PATH.exists()


def main() -> int:
    migration_ok = run_migration_smoke()
    with TestClient(app) as client:
        db = SessionLocal()
        try:
            reader = User(
                id="user-reader-test",
                email="reader@local.test",
                name="Reader Test",
                role="reader",
                password_hash=hash_password("reader123"),
                is_active=True,
                created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                updated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            )
            db.merge(reader)
            db.commit()
        finally:
            db.close()

        unauth_settings = client.get("/api/settings")
        admin_login = client.post("/api/auth/login", json={"email": DEV_ADMIN_EMAIL, "password": DEV_ADMIN_PASSWORD})
        admin_token = admin_login.json()["token"] if admin_login.status_code == 200 else ""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        me = client.get("/api/auth/me", headers=admin_headers)
        admin_settings = client.get("/api/settings", headers=admin_headers)
        publish = client.post("/api/pages/page-004/publish", headers=admin_headers)

        reader_login = client.post("/api/auth/login", json={"email": "reader@local.test", "password": "reader123"})
        reader_token = reader_login.json()["token"] if reader_login.status_code == 200 else ""
        reader_headers = {"Authorization": f"Bearer {reader_token}"}
        reader_settings = client.get("/api/settings", headers=reader_headers)
        reader_publish = client.post("/api/pages/page-004/unpublish", headers=reader_headers)

        db = SessionLocal()
        try:
            audit = (
                db.query(AuditLog)
                .filter(AuditLog.action == "publish", AuditLog.object_id == "page-004")
                .order_by(AuditLog.created_at.desc())
                .first()
            )
            audit_actor = audit.actor if audit else None
            audit_role = (audit.metadata_json or {}).get("actorRole") if audit else None
        finally:
            db.close()

        logout = client.post("/api/auth/logout", headers=admin_headers)
        me_after_logout = client.get("/api/auth/me", headers=admin_headers)

    payload = {
        "success": True,
        "migrationOk": migration_ok,
        "unauthSettings": unauth_settings.status_code,
        "adminLogin": admin_login.status_code,
        "meRole": me.json().get("role") if me.status_code == 200 else None,
        "adminSettings": admin_settings.status_code,
        "publishStatus": publish.status_code,
        "readerLogin": reader_login.status_code,
        "readerSettings": reader_settings.status_code,
        "readerPublish": reader_publish.status_code,
        "auditActor": audit_actor,
        "auditRole": audit_role,
        "logout": logout.status_code,
        "meAfterLogout": me_after_logout.status_code,
    }
    checks = [
        payload["migrationOk"],
        payload["unauthSettings"] == 401,
        payload["adminLogin"] == 200,
        payload["meRole"] == "admin",
        payload["adminSettings"] == 200,
        payload["publishStatus"] == 200,
        payload["readerLogin"] == 200,
        payload["readerSettings"] == 403,
        payload["readerPublish"] == 403,
        payload["auditActor"] == "Dev Admin",
        payload["auditRole"] == "admin",
        payload["logout"] == 200,
        payload["meAfterLogout"] == 401,
    ]
    if not all(checks):
        payload["success"] = False
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

