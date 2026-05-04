from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.database import Base
from app.models import AuditLog
from app.services.settings import serialize_runtime_settings, update_runtime_settings
from app.core.runtime_config import ensure_runtime_config, runtime_snapshot_from_record


def main() -> None:
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    session = SessionLocal()
    try:
        initial = serialize_runtime_settings(session)
        payload = {**initial}
        payload["aiTaskProfiles"] = {
            **initial["aiTaskProfiles"],
            "ask_answer": {
                "provider": "ollama",
                "model": "ask-model",
                "apiKey": "",
                "baseUrl": "http://host.docker.internal:11434",
                "timeoutSeconds": 120,
            },
            "bpm_generation": {
                "provider": "openai_compatible",
                "model": "bpm-model",
                "apiKey": "secret-bpm",
                "baseUrl": "http://llm.internal/v1",
                "timeoutSeconds": 150,
            },
            "embeddings": {
                "provider": "ollama",
                "model": "nomic-embed-text",
                "apiKey": "",
                "baseUrl": "http://host.docker.internal:11434",
                "timeoutSeconds": 90,
            },
        }
        payload["chunkMode"] = "structured"
        updated = update_runtime_settings(session, payload, actor_name="Phase31 Test")

        assert updated["aiTaskProfiles"]["ask_answer"]["model"] == "ask-model", updated
        assert updated["aiTaskProfiles"]["bpm_generation"]["model"] == "bpm-model", updated
        assert updated["answerModel"] == "ask-model", updated
        assert updated["embeddingModel"] == "nomic-embed-text", updated

        record = ensure_runtime_config(session)
        snapshot = runtime_snapshot_from_record(record)
        assert snapshot.profile_for_task("ask_answer").model == "ask-model"
        assert snapshot.profile_for_task("bpm_generation").model == "bpm-model"
        assert snapshot.profile_for_task("embeddings").model == "nomic-embed-text"
        assert snapshot.answer_llm.model == "ask-model"

        audits = session.query(AuditLog).filter(AuditLog.object_type == "runtime_config").all()
        assert audits, "Expected runtime settings audit log"
        print(
            {
                "success": True,
                "askModel": snapshot.profile_for_task("ask_answer").model,
                "bpmModel": snapshot.profile_for_task("bpm_generation").model,
                "embeddingModel": snapshot.profile_for_task("embeddings").model,
                "auditCount": len(audits),
            }
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
