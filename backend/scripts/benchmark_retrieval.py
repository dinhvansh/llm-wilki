from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK_DB = ROOT / "benchmark_retrieval.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{DEFAULT_BENCHMARK_DB.as_posix()}")
os.environ.setdefault("AUTO_SEED_DEMO_DATA", "true")
os.environ.setdefault("JOB_QUEUE_BACKEND", "database")
os.environ.setdefault("DEBUG", "true")
REPORT_JSON = ROOT / "evals" / "last_benchmark_report.json"
REPORT_MD = ROOT / "evals" / "last_benchmark_report.md"


def _reset_stale_default_benchmark_db() -> None:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url.startswith("sqlite:///"):
        return
    db_path = Path(database_url.removeprefix("sqlite:///"))
    if db_path.resolve() != DEFAULT_BENCHMARK_DB.resolve() or not db_path.exists():
        return
    try:
        with sqlite3.connect(db_path) as conn:
            user_columns = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
            source_columns = {row[1] for row in conn.execute("PRAGMA table_info(sources)").fetchall()}
    except sqlite3.Error:
        user_columns = set()
        source_columns = set()
    if {"department_id"} <= user_columns and {"scope_type", "workspace_id", "collection_id"} <= source_columns:
        return
    try:
        db_path.unlink(missing_ok=True)
    except PermissionError:
        runtime_db = ROOT / f"benchmark_retrieval_runtime_{os.getpid()}.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{runtime_db.as_posix()}"


_reset_stale_default_benchmark_db()
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.core.ingest import split_into_structured_chunks, split_into_window_chunks  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.models import Source, SourceChunk  # noqa: E402
from app.services.quality_runs import create_eval_run  # noqa: E402
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


def _seed_section_summary_benchmark(db) -> None:
    existing = db.query(Source).filter(Source.id == "src-bench-sop").first()
    if existing:
        return
    source = Source(
        id="src-bench-sop",
        title="Access Approval SOP",
        source_type="markdown",
        mime_type="text/markdown",
        file_path=None,
        url=None,
        uploaded_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        created_by="benchmark",
        parse_status="completed",
        ingest_status="completed",
        metadata_json={
            "documentType": "sop",
            "authorityLevel": "official",
            "sourceStatus": "approved",
            "notebookContext": {
                "documentType": "sop",
                "sourceBrief": "This SOP explains prerequisites, validation, and escalation for access approval.",
                "keyPoints": [
                    "A request and manager approval must exist first.",
                    "Privileged access requests escalate to security.",
                ],
                "notes": [
                    {
                        "id": "note-bench-prereq",
                        "kind": "summary",
                        "title": "Prerequisites",
                        "text": "User account and manager request must exist before approval starts.",
                        "roles": ["summary", "definition"],
                        "provenance": {"sourceId": "src-bench-sop", "chunkIds": ["chunk-bench-sop-1"], "sectionKeys": ["sec-prereq"]},
                    },
                    {
                        "id": "note-bench-step",
                        "kind": "procedure",
                        "title": "First step",
                        "text": "The first step is to open the request queue and validate requester identity.",
                        "roles": ["step", "summary"],
                        "provenance": {"sourceId": "src-bench-sop", "chunkIds": ["chunk-bench-sop-1"], "sectionKeys": ["sec-step1"]},
                    },
                ],
                "recommendedPrompts": [
                    "What prerequisites should I check first?",
                    "What step should I follow first?",
                ],
            },
            "sectionSummaries": [
                {
                    "sectionKey": "sec-prereq",
                    "title": "Prerequisites",
                    "summary": "User account and manager request must exist before approval starts.",
                    "roles": ["prerequisite"],
                    "headingPath": ["Prerequisites"],
                    "chunkCount": 1,
                },
                {
                    "sectionKey": "sec-step1",
                    "title": "Step 1",
                    "summary": "Open the request queue and validate requester identity.",
                    "roles": ["step"],
                    "headingPath": ["Step 1"],
                    "chunkCount": 1,
                },
                {
                    "sectionKey": "sec-exception",
                    "title": "Exception",
                    "summary": "Escalate to security if the request includes privileged access.",
                    "roles": ["exception"],
                    "headingPath": ["Exception"],
                    "chunkCount": 1,
                },
            ],
        },
        checksum="src-bench-sop",
        trust_level="high",
        file_size=None,
        description="Access approval procedure for privileged access requests.",
        tags=["sop", "access"],
        collection_id=None,
    )
    chunk = SourceChunk(
        id="chunk-bench-sop-1",
        source_id=source.id,
        chunk_index=0,
        section_title="Step 1",
        page_number=1,
        content="Open the request queue and validate requester identity before any approval.",
        token_count=11,
        embedding_id=None,
        metadata_json={"sectionRole": "step", "parentSectionSummary": "Open the request queue and validate requester identity."},
        span_start=0,
        span_end=79,
        created_at=datetime.now(timezone.utc),
    )
    db.add_all([source, chunk])
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


def write_reports(report: dict) -> None:
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Retrieval Benchmark Report",
        "",
        f"- Success: {report['success']}",
        f"- Query count: {report['queryCount']}",
        "",
        "## Quality Gates",
    ]
    for key, value in (report.get("qualityGates") or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Search", ""])
    for item in report.get("search", []):
        lines.append(f"- `{item['query']}` hits={item['hits']} top={item['top']} latencyMs={item['ms']}")
    lines.extend(["", "## Ask", ""])
    for item in report.get("ask", []):
        lines.append(f"- `{item['query']}` citations={item['citations']} candidates={item['candidateCount']} latencyMs={item['ms']}")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)
        _seed_authority_benchmark(db)
        _seed_section_summary_benchmark(db)
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
        section_query = "What are the prerequisites before access approval starts?"
        section_answer = ask(db, section_query)
        section_summary_signal = {
            "query": section_query,
            "topCandidateTypes": [item.get("candidateType") for item in ((section_answer.get("diagnostics") or {}).get("topCandidates") or [])[:5]],
            "selectedContextTypes": [item.get("candidateType") for item in ((section_answer.get("diagnostics") or {}).get("selectedContext") or [])[:5]],
            "hasSectionSummaryCandidate": any(item.get("candidateType") == "section_summary" for item in ((section_answer.get("diagnostics") or {}).get("topCandidates") or [])),
        }
        notebook_query = "Give a summary of the access approval SOP."
        notebook_answer = ask(db, notebook_query, source_id="src-bench-sop")
        notebook_signal = {
            "query": notebook_query,
            "topCandidateTypes": [item.get("candidateType") for item in ((notebook_answer.get("diagnostics") or {}).get("topCandidates") or [])[:5]],
            "selectedContextTypes": [item.get("candidateType") for item in ((notebook_answer.get("diagnostics") or {}).get("selectedContext") or [])[:5]],
            "hasNotebookContextCandidate": any(item.get("candidateType") in {"notebook_note", "section_summary"} for item in ((notebook_answer.get("diagnostics") or {}).get("topCandidates") or [])),
        }
        quality_gates = {
            "authoritySignal": authority_before_after["improvedHasConflictSignal"] and authority_before_after["improvedHasRerankSignal"],
            "sectionSummarySignal": section_summary_signal["hasSectionSummaryCandidate"],
            "notebookContextSignal": notebook_signal["hasNotebookContextCandidate"],
            "structuredChunkCountBetterOrEqual": chunk_mode_comparison["structured"]["chunkCount"] >= 2,
            "structuredCitationStable": chunk_mode_comparison["structured"]["citationStability"] >= 0.9,
        }
        quality_gates["allPassed"] = all(bool(value) for value in quality_gates.values())

        report = {
            "success": quality_gates["allPassed"],
            "queryCount": len(QUERIES),
            "search": search_runs,
            "ask": ask_runs,
            "chunkModeComparison": chunk_mode_comparison,
            "authorityBeforeAfter": authority_before_after,
            "sectionSummarySignal": section_summary_signal,
            "notebookSignal": notebook_signal,
            "qualityGates": quality_gates,
        }
        create_eval_run(
            db,
            run_type="benchmark",
            run_name="retrieval-benchmark",
            version="phase4-benchmark-v1",
            report=report,
            tags=["retrieval", "benchmark", "phase4"],
        )
        write_reports(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
