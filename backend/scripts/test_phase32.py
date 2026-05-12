from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.ingest import IngestArtifacts, IngestStageResult, ParsedDocument
from app.db.database import Base
from app.models import Source
from app.services import sources as source_service


def main() -> None:
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    session = SessionLocal()

    with tempfile.TemporaryDirectory() as tmp_dir:
        source_path = Path(tmp_dir) / "semantic-source.txt"
        source_path.write_text("Tai lieu quy dinh nghiep vu.", encoding="utf-8")

        source = Source(
            id="src-semantic",
            title="Semantic Source",
            source_type="txt",
            mime_type="text/plain",
            file_path=str(source_path),
            url=None,
            uploaded_at=source_service.datetime.now(source_service.timezone.utc),
            updated_at=source_service.datetime.now(source_service.timezone.utc),
            created_by="Phase32 Test",
            parse_status="uploaded",
            ingest_status="uploaded",
            metadata_json={},
            checksum="semantic",
            trust_level="medium",
            file_size=source_path.stat().st_size,
            description="",
            tags=[],
            collection_id=None,
        )
        session.add(source)
        session.commit()

        artifacts = IngestArtifacts(
            parsed=ParsedDocument(
                text="Nhan vien phai nop bao cao trong 7 ngay.",
                mime_type="text/plain",
                source_type="txt",
                metadata={"orderedBlocks": []},
            ),
            chunks=[
                {
                    "section_title": "Submission Rules",
                    "content": "Nhan vien phai nop bao cao trong 7 ngay.",
                    "token_count": 8,
                    "metadata": {"headingPath": ["Submission Rules"], "blockTypes": ["paragraph"]},
                }
            ],
            summary="Quy dinh nop bao cao.",
            key_facts=["Nhan vien phai nop bao cao trong 7 ngay."],
            tags=["policy", "reporting"],
            entities=[
                {
                    "id": "ent-user",
                    "name": "Nhan vien",
                    "entity_type": "person",
                    "description": "Nguoi nop bao cao",
                    "aliases": [],
                    "normalized_name": "nhan-vien",
                    "mention_count": 1,
                    "confidence_score": 0.8,
                }
            ],
            claims=[
                {
                    "id": "clm-semantic",
                    "text": "Nhan vien phai nop bao cao trong 7 ngay.",
                    "claim_type": "requirement",
                    "confidence_score": 0.86,
                    "canonical_status": "unverified",
                    "review_status": "pending",
                    "topic": "Submission Rules",
                    "entity_ids": ["ent-user"],
                    "chunk_index": 0,
                    "extraction_method": "llm",
                    "evidence_span_start": 0,
                    "evidence_span_end": 39,
                    "metadata_json": {"evidenceExcerpt": "Nhan vien phai nop bao cao trong 7 ngay.", "promptVersion": "test"},
                }
            ],
            timeline_events=[],
            glossary_terms=[],
            page_type_candidates=[{"pageType": "sop", "confidence": 0.91, "reason": "Contains procedural requirement"}],
            stage_results=[
                IngestStageResult(name="parse", status="completed", details={"sourceType": "txt"}),
                IngestStageResult(name="extract_claims", status="completed", details={"claimCount": 1}),
            ],
        )

        original_pipeline = source_service.run_ingest_pipeline
        original_embed = source_service.embedding_client.embed_texts
        try:
            source_service.run_ingest_pipeline = lambda *args, **kwargs: artifacts
            source_service.embedding_client.embed_texts = lambda *args, **kwargs: None
            result = source_service.ingest_source(session, "src-semantic")
        finally:
            source_service.run_ingest_pipeline = original_pipeline
            source_service.embedding_client.embed_texts = original_embed

        assert result is not None, "Expected source ingest result"
        knowledge_units = source_service.get_source_knowledge_units(session, "src-semantic")
        extraction_runs = source_service.get_source_extraction_runs(session, "src-semantic")

        assert knowledge_units, "Expected knowledge units"
        assert knowledge_units[0]["unitType"] == "rule", knowledge_units
        assert knowledge_units[0]["claimId"] == "clm-semantic", knowledge_units
        assert extraction_runs, "Expected extraction runs"
        run_types = {run["runType"] for run in extraction_runs}
        assert "claim_extraction" in run_types, extraction_runs
        assert "entity_extraction" in run_types, extraction_runs
        assert any(run["method"] in {"llm", "hybrid"} for run in extraction_runs if run["runType"] == "claim_extraction"), extraction_runs

        print(
            {
                "success": True,
                "knowledgeUnitCount": len(knowledge_units),
                "extractionRunTypes": sorted(run_types),
                "firstKnowledgeUnit": knowledge_units[0]["text"],
            }
        )

    session.close()


if __name__ == "__main__":
    main()
