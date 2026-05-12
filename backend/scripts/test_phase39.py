from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.ingest import IngestArtifacts, IngestStageResult, ParsedDocument  # noqa: E402
from app.db.database import Base  # noqa: E402
from app.models import Source  # noqa: E402
from app.services import sources as source_service  # noqa: E402


def main() -> None:
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    session = SessionLocal()

    with tempfile.TemporaryDirectory() as tmp_dir:
        source_path = Path(tmp_dir) / "knowledge-unit-source.txt"
        source_path.write_text("Dummy policy source.", encoding="utf-8")

        source = Source(
            id="src-phase39",
            title="Normalized Unit Source",
            source_type="txt",
            mime_type="text/plain",
            file_path=str(source_path),
            url=None,
            uploaded_at=source_service.datetime.now(source_service.timezone.utc),
            updated_at=source_service.datetime.now(source_service.timezone.utc),
            created_by="Phase39 Test",
            parse_status="uploaded",
            ingest_status="uploaded",
            metadata_json={"sourceStatus": "approved", "authorityLevel": "official"},
            checksum="phase39",
            trust_level="high",
            file_size=source_path.stat().st_size,
            description="",
            tags=[],
            collection_id=None,
        )
        session.add(source)
        session.commit()

        artifacts = IngestArtifacts(
            parsed=ParsedDocument(
                text="Policy and procedure source.",
                mime_type="text/plain",
                source_type="txt",
                metadata={"documentType": "policy", "sectionSummaries": [], "language": "en"},
            ),
            chunks=[
                {
                    "section_title": "Rules",
                    "content": "Changes affecting more than 5000 users require CAB approval.",
                    "token_count": 9,
                    "metadata": {"sectionRole": "rule", "headingPath": ["Rules"]},
                },
                {
                    "section_title": "Procedure",
                    "content": "Open the queue and validate requester identity.",
                    "token_count": 8,
                    "metadata": {"sectionRole": "step", "headingPath": ["Procedure"]},
                },
                {
                    "section_title": "Risks",
                    "content": "Warning: privileged changes can cause service disruption.",
                    "token_count": 8,
                    "metadata": {"sectionRole": "warning", "headingPath": ["Risks"]},
                },
            ],
            summary="Policy and procedure source.",
            key_facts=["Threshold, step, and warning claims are present."],
            tags=["policy", "procedure"],
            entities=[],
            claims=[
                {
                    "id": "clm-threshold",
                    "text": "Changes affecting more than 5000 users require CAB approval.",
                    "claim_type": "requirement",
                    "confidence_score": 0.91,
                    "canonical_status": "verified",
                    "review_status": "approved",
                    "topic": "Rules",
                    "entity_ids": [],
                    "chunk_index": 0,
                    "extraction_method": "llm",
                    "evidence_span_start": 0,
                    "evidence_span_end": 58,
                    "metadata_json": {"sectionRole": "rule"},
                },
                {
                    "id": "clm-step",
                    "text": "Open the queue and validate requester identity.",
                    "claim_type": "instruction",
                    "confidence_score": 0.88,
                    "canonical_status": "verified",
                    "review_status": "approved",
                    "topic": "Procedure",
                    "entity_ids": [],
                    "chunk_index": 1,
                    "extraction_method": "llm",
                    "evidence_span_start": 0,
                    "evidence_span_end": 47,
                    "metadata_json": {"sectionRole": "step"},
                },
                {
                    "id": "clm-warning",
                    "text": "Privileged changes can cause service disruption.",
                    "claim_type": "risk",
                    "confidence_score": 0.82,
                    "canonical_status": "verified",
                    "review_status": "approved",
                    "topic": "Risks",
                    "entity_ids": [],
                    "chunk_index": 2,
                    "extraction_method": "llm",
                    "evidence_span_start": 0,
                    "evidence_span_end": 48,
                    "metadata_json": {"sectionRole": "warning"},
                },
            ],
            timeline_events=[],
            glossary_terms=[],
            page_type_candidates=[{"pageType": "sop", "confidence": 0.8, "reason": "Has procedure steps"}],
            stage_results=[IngestStageResult(name="parse", status="completed", details={"sourceType": "txt"})],
        )

        original_pipeline = source_service.run_ingest_pipeline
        original_embed = source_service.embedding_client.embed_texts
        try:
            source_service.run_ingest_pipeline = lambda *args, **kwargs: artifacts
            source_service.embedding_client.embed_texts = lambda *args, **kwargs: None
            result = source_service.ingest_source(session, source.id)
        finally:
            source_service.run_ingest_pipeline = original_pipeline
            source_service.embedding_client.embed_texts = original_embed

        assert result is not None, "Expected source ingest result"
        units = source_service.get_source_knowledge_units(session, source.id)
        unit_types = sorted(unit["unitType"] for unit in units)
        assert "threshold" in unit_types, unit_types
        assert "procedure_step" in unit_types, unit_types
        assert "warning" in unit_types, unit_types
        print({"success": True, "unitTypes": unit_types})

    session.close()


if __name__ == "__main__":
    main()
