from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_ask_history.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.services.query import ask, delete_chat_session, get_chat_session, list_chat_sessions  # noqa: E402


def main() -> int:
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)

        first = ask(db, "What is RAG?")
        second = ask(db, "What standards are required?", first["sessionId"])
        sessions = list_chat_sessions(db)
        detail = get_chat_session(db, first["sessionId"])
        deleted = delete_chat_session(db, first["sessionId"])
        missing = get_chat_session(db, first["sessionId"])

        payload = {
            "success": True,
            "firstSessionId": first.get("sessionId"),
            "secondSessionId": second.get("sessionId"),
            "sessionCount": len(sessions),
            "detailMessageCount": detail.get("messageCount") if detail else None,
            "roles": [message["role"] for message in detail.get("messages", [])] if detail else [],
            "deleted": deleted,
            "missingAfterDelete": missing is None,
        }
        checks = [
            payload["firstSessionId"],
            payload["firstSessionId"] == payload["secondSessionId"],
            payload["sessionCount"] >= 1,
            payload["detailMessageCount"] == 4,
            payload["roles"] == ["user", "assistant", "user", "assistant"],
            payload["deleted"],
            payload["missingAfterDelete"],
        ]
        if not all(checks):
            payload["success"] = False
            payload["message"] = "Ask chat history checks failed"
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1

        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
