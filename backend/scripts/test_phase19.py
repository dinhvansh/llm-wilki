from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase19.db"
MIGRATION_DB_PATH = ROOT / "test_phase19_migration.db"
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
from app.models import Page, ReviewItem, SourceChunk  # noqa: E402
from app.services.auth import DEV_ADMIN_EMAIL, DEV_ADMIN_PASSWORD  # noqa: E402


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
        login = client.post("/api/auth/login", json={"email": DEV_ADMIN_EMAIL, "password": DEV_ADMIN_PASSWORD})
        token = login.json()["token"] if login.status_code == 200 else ""
        headers = {"Authorization": f"Bearer {token}"}

        page = client.get("/api/pages/llm-integration-standards").json()
        page_id = page["id"]
        version = page["currentVersion"]
        update_ok = client.post(
            f"/api/pages/{page_id}/update",
            headers=headers,
            json={"contentMd": page["contentMd"] + "\n\nPhase 19 draft edit.", "changeSummary": "Phase 19 draft", "expectedVersion": version},
        )
        conflict = client.post(
            f"/api/pages/{page_id}/update",
            headers=headers,
            json={"contentMd": "stale overwrite", "changeSummary": "Should conflict", "expectedVersion": version},
        )
        restore = client.post(f"/api/pages/{page_id}/restore-version", headers=headers, json={"versionNo": version})
        helpers = client.get(f"/api/pages/{page_id}/insert-helpers")

        db = SessionLocal()
        try:
            review_id = db.query(ReviewItem.id).first()[0]
            chunk_ids = [row[0] for row in db.query(SourceChunk.id).limit(2).all()]
            issue_page = Page(
                id="page-phase19-issue",
                slug="phase19-issue",
                title="Phase19 Issue",
                page_type="issue",
                status="draft",
                summary="Issue page for Phase 19 quick fix test.",
                content_md="# Phase19 Issue\n\n## Risk And Impact\n\n- **Owner:** TBD\n- **Status:** TBD",
                content_html=None,
                current_version=1,
                last_composed_at=datetime.now(timezone.utc),
                last_reviewed_at=None,
                published_at=None,
                owner="Phase19 Test",
                tags=["issue"],
                parent_page_id=None,
                key_facts=[],
                related_page_ids=[],
                related_entity_ids=[],
                collection_id=None,
            )
            db.merge(issue_page)
            db.commit()
        finally:
            db.close()

        comment = client.post(f"/api/review-items/{review_id}/comments", headers=headers, json={"comment": "Phase 19 review thread note"})
        saved = client.post("/api/saved-views", headers=headers, json={"name": "High severity lint", "viewType": "lint", "filters": {"severity": "high"}})
        saved_list = client.get("/api/saved-views?viewType=lint", headers=headers)
        bulk_pages = client.post("/api/pages/bulk", headers=headers, json={"pageIds": [page_id], "action": "unpublish"})
        bulk_sources = client.post("/api/sources/bulk", headers=headers, json={"sourceIds": ["src-001"], "action": "archive"})
        quick_fix = client.post("/api/lint/actions", headers=headers, json={"action": "edit_issue_fields", "payload": {"pageId": "page-phase19-issue"}})
        from_chunks = client.post("/api/pages/from-chunks", headers=headers, json={"title": "Phase 19 Chunk Draft", "chunkIds": chunk_ids})
        ask = client.post("/api/ask", json={"question": "What are the LLM integration standards?"})
        ask_message_id = ask.json().get("id") if ask.status_code == 200 else None
        ask_draft = client.post("/api/ask/save-draft", headers=headers, json={"messageId": ask_message_id, "title": "Phase 19 Ask Draft"})

    payload = {
        "success": True,
        "migrationOk": migration_ok,
        "login": login.status_code,
        "updateOk": update_ok.status_code,
        "conflict": conflict.status_code,
        "restore": restore.status_code,
        "helpers": helpers.status_code,
        "reviewComment": comment.status_code,
        "savedView": saved.status_code,
        "savedViewCount": len(saved_list.json()) if saved_list.status_code == 200 else None,
        "bulkPages": bulk_pages.json().get("updatedCount") if bulk_pages.status_code == 200 else None,
        "bulkSources": bulk_sources.json().get("updatedCount") if bulk_sources.status_code == 200 else None,
        "quickFix": quick_fix.json().get("success") if quick_fix.status_code == 200 else None,
        "fromChunks": from_chunks.status_code,
        "askDraft": ask_draft.status_code,
    }
    checks = [
        payload["migrationOk"],
        payload["login"] == 200,
        payload["updateOk"] == 200,
        payload["conflict"] == 409,
        payload["restore"] == 200,
        payload["helpers"] == 200,
        payload["reviewComment"] == 200,
        payload["savedView"] == 200,
        (payload["savedViewCount"] or 0) >= 1,
        payload["bulkPages"] == 1,
        payload["bulkSources"] == 1,
        payload["quickFix"] is True,
        payload["fromChunks"] == 200,
        payload["askDraft"] == 200,
    ]
    if not all(checks):
        payload["success"] = False
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
