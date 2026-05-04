from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("DATABASE_URL", f"sqlite:///{(ROOT / 'benchmark_retrieval.db').as_posix()}")
os.environ.setdefault("AUTO_SEED_DEMO_DATA", "true")
os.environ.setdefault("JOB_QUEUE_BACKEND", "database")
os.environ.setdefault("DEBUG", "true")
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.core.ingest import split_into_structured_chunks, split_into_window_chunks  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.models import Source, SourceChunk  # noqa: E402
from app.services.query import ask, search  # noqa: E402


QUERIES = [
    "citation accuracy",
    "hybrid retrieval",
    "safety evaluation framework",
    "API authentication",
]

CHUNK_BENCHMARK_DOC = """
# Expense Reimbursement Workflow

## Submission Steps

1. Employee completes the expense form within 7 days.
2. Employee attaches receipts and supporting files.
3. Finance validates required fields and tax evidence.

## Approval Rules

- If receipts are missing, the manager must approve an exception.
- If the claim exceeds budget, finance escalates to the department head.

## SLA Metrics

| Stage | Owner | SLA |
| --- | --- | --- |
| Submission review | Finance | 2 business days |
| Exception review | Manager | 1 business day |
| Final reimbursement | Finance | 3 business days |

## Notes

The claimant may sometimes add extra context when the system cannot classify a receipt automatically.
""".strip()

ANCHORS = [
    "Employee completes the expense form within 7 days.",
    "If receipts are missing, the manager must approve an exception.",
    "| Submission review | Finance | 2 business days |",
]


def _seed_authority_benchmark(db) -> None:
    existing = db.query(Source).filter(Source.id == "src-bench-approved").first()
    if existing:
        return
    source_a = Source(
        id="src-bench-approved",
        title="Approved Credit Policy",
        source_type="markdown",
        mime_type="text/markdown",
        file_path=None,
        url=None,
        uploaded_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        created_by="benchmark",
        parse_status="completed",
        ingest_status="completed",
        metadata_json={"authorityLevel": "official", "sourceStatus": "approved"},
        checksum="src-bench-approved",
        trust_level="high",
        file_size=None,
        description=None,
        tags=["policy"],
        collection_id=None,
    )
    source_b = Source(
        id="src-bench-note",
        title="Meeting Note Credit Policy",
        source_type="markdown",
        mime_type="text/markdown",
        file_path=None,
        url=None,
        uploaded_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        created_by="benchmark",
        parse_status="completed",
        ingest_status="completed",
        metadata_json={"authorityLevel": "informal", "sourceStatus": "draft"},
        checksum="src-bench-note",
        trust_level="medium",
        file_size=None,
        description=None,
        tags=["meeting_note"],
        collection_id=None,
    )
    chunk_a = SourceChunk(
        id="chunk-bench-approved",
        source_id=source_a.id,
        chunk_index=0,
        section_title="Credit policy rule",
        page_number=1,
        content="Credit approval threshold is 100,000 USD and finance must escalate anything above that amount.",
        token_count=14,
        embedding_id=None,
        metadata_json={},
        span_start=0,
        span_end=95,
        created_at=datetime.now(timezone.utc),
    )
    chunk_b = SourceChunk(
        id="chunk-bench-note",
        source_id=source_b.id,
        chunk_index=0,
        section_title="Credit policy note",
        page_number=1,
        content="Credit approval threshold is 90,000 USD according to a meeting note draft that has not been approved.",
        token_count=17,
        embedding_id=None,
        metadata_json={},
        span_start=0,
        span_end=102,
        created_at=datetime.now(timezone.utc),
    )
    db.add_all([source_a, source_b, chunk_a, chunk_b])
    db.commit()


def _legacy_chunk_only_top_source(db, query: str) -> str | None:
    terms = [token for token in query.lower().split() if len(token) >= 3]
    scored: list[tuple[float, str]] = []
    for chunk, source in db.query(SourceChunk, Source).join(Source, SourceChunk.source_id == Source.id).all():
        text = f"{source.title}\n{chunk.section_title}\n{chunk.content}".lower()
        score = sum(1 for term in terms if term in text)
        if score > 0:
            scored.append((float(score), source.title))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1] if scored else None


def _avg_words(chunks: list[dict]) -> float:
    if not chunks:
        return 0.0
    return round(mean(len((chunk.get("content") or "").split()) for chunk in chunks), 2)


def _chunk_mode_report(name: str, chunks: list[dict]) -> dict:
    anchor_results: list[dict] = []
    stable_hits = 0
    for anchor in ANCHORS:
        matching = [chunk for chunk in chunks if anchor in str(chunk.get("content") or "")]
        chunk = matching[0] if matching else {}
        metadata = chunk.get("metadata") or {}
        exact_one = len(matching) == 1
        stable_hits += 1 if exact_one else 0
        anchor_results.append(
            {
                "anchor": anchor[:60],
                "exactOneChunk": exact_one,
                "sectionTitle": chunk.get("section_title"),
                "headingPath": metadata.get("headingPath", []),
                "blockTypes": metadata.get("blockTypes", []),
            }
        )

    return {
        "mode": name,
        "chunkCount": len(chunks),
        "avgWords": _avg_words(chunks),
        "citationStability": round(stable_hits / max(len(ANCHORS), 1), 2),
        "anchorResults": anchor_results,
    }


def main() -> int:
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)
        _seed_authority_benchmark(db)
        search_runs = []
        ask_runs = []
        for query in QUERIES:
            started = perf_counter()
            results = search(db, query, limit=10)
            search_runs.append(
                {
                    "query": query,
                    "ms": round((perf_counter() - started) * 1000, 2),
                    "hits": len(results),
                    "top": results[0]["title"] if results else None,
                }
            )
            started = perf_counter()
            answer = ask(db, query)
            ask_runs.append(
                {
                    "query": query,
                    "ms": round((perf_counter() - started) * 1000, 2),
                    "citations": len(answer["citations"]),
                    "candidateCount": answer.get("diagnostics", {}).get("candidateCount"),
                }
            )

        structured = split_into_structured_chunks(CHUNK_BENCHMARK_DOC, max_words=180, overlap=30)
        window = split_into_window_chunks(CHUNK_BENCHMARK_DOC, max_words=180, overlap=30)
        chunk_mode_comparison = {
            "structured": _chunk_mode_report("structured", structured),
            "window": _chunk_mode_report("window", window),
        }
        authority_query = "What is the credit approval threshold policy?"
        improved = ask(db, authority_query)
        authority_before_after = {
            "query": authority_query,
            "legacyChunkOnlyTopSource": _legacy_chunk_only_top_source(db, authority_query),
            "improvedPreferredSource": ((improved.get("conflicts") or [{}])[0].get("preferredSourceTitle") or (improved.get("relatedSources") or [{}])[0].get("title")),
            "improvedTopCandidateType": ((improved.get("diagnostics") or {}).get("topCandidates") or [{}])[0].get("candidateType"),
            "improvedHasConflictSignal": len(improved.get("conflicts") or []) > 0,
            "improvedHasRerankSignal": ((improved.get("diagnostics") or {}).get("topCandidates") or [{}])[0].get("rerankScore") is not None,
        }

        report = {
            "success": True,
            "queryCount": len(QUERIES),
            "search": search_runs,
            "ask": ask_runs,
            "chunkModeComparison": chunk_mode_comparison,
            "authorityBeforeAfter": authority_before_after,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
