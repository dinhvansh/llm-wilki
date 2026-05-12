from __future__ import annotations

import json
import os
import sqlite3
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "evals" / "golden_dataset.json"
REPORT_JSON = ROOT / "evals" / "last_eval_report.json"
REPORT_MD = ROOT / "evals" / "last_eval_report.md"
DEFAULT_EVAL_DB = ROOT / "quality_eval.db"

os.environ.setdefault("DATABASE_URL", f"sqlite:///{DEFAULT_EVAL_DB.as_posix()}")
os.environ.setdefault("AUTO_SEED_DEMO_DATA", "true")
os.environ.setdefault("JOB_QUEUE_BACKEND", "database")
os.environ.setdefault("DEBUG", "true")


def _reset_stale_default_eval_db() -> None:
    """Recreate the throwaway SQLite eval DB before SQLAlchemy opens it."""
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url.startswith("sqlite:///"):
        return
    db_path = Path(database_url.removeprefix("sqlite:///"))
    if db_path.resolve() != DEFAULT_EVAL_DB.resolve() or not db_path.exists():
        return
    try:
        with sqlite3.connect(db_path) as conn:
            user_columns = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
            source_columns = {row[1] for row in conn.execute("PRAGMA table_info(sources)").fetchall()}
    except sqlite3.Error:
        user_columns = set()
        source_columns = set()
    required_user_columns = {"department_id"}
    required_source_columns = {"scope_type", "workspace_id", "collection_id"}
    if not user_columns or not source_columns or not required_user_columns <= user_columns or not required_source_columns <= source_columns:
        try:
            db_path.unlink(missing_ok=True)
        except PermissionError:
            runtime_db = ROOT / f"quality_eval_runtime_{os.getpid()}.db"
            os.environ["DATABASE_URL"] = f"sqlite:///{runtime_db.as_posix()}"


_reset_stale_default_eval_db()
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.core.ingest import build_page_markdown, json_like_to_dict, summarize_text  # noqa: E402
from app.core.reliability import EVAL_VERSION, REVIEW_REASON_TAXONOMY, calibrate_confidence  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.services.quality_runs import create_eval_run  # noqa: E402
from app.services.lint import run_lint  # noqa: E402
from app.models import Source, SourceChunk  # noqa: E402
from app.services.query import ask, search  # noqa: E402


def _term_hits(text: str, terms: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if term.lower() in lowered)


def _candidate_source_ids(answer: dict, limit: int) -> list[str]:
    diagnostics = answer.get("diagnostics", {}) or {}
    seen: list[str] = []
    for item in (diagnostics.get("topCandidates") or [])[:limit]:
        source_id = item.get("sourceId")
        if source_id and source_id not in seen:
            seen.append(source_id)
    return seen


def _recall_at_k(retrieved_source_ids: list[str], expected_source_ids: list[str], k: int) -> float:
    expected = {item for item in expected_source_ids if item}
    if not expected:
        return 0.0
    retrieved = set(retrieved_source_ids[:k])
    return round(len(retrieved & expected) / len(expected), 4)


def _precision_at_k(retrieved_source_ids: list[str], expected_source_ids: list[str], k: int) -> float:
    considered = [item for item in retrieved_source_ids[:k] if item]
    if not considered:
        return 0.0
    expected = {item for item in expected_source_ids if item}
    return round(sum(1 for item in considered if item in expected) / len(considered), 4)


def _filter_cases_by_tags(cases: list[dict], selected_tags: list[str] | None) -> list[dict]:
    if not selected_tags:
        return cases
    selected = {tag.strip().lower() for tag in selected_tags if tag.strip()}
    if not selected:
        return cases
    filtered = []
    for case in cases:
        case_tags = {str(tag).strip().lower() for tag in case.get("tags", []) if str(tag).strip()}
        if case_tags & selected:
            filtered.append(case)
    return filtered


def _seed_conflict_sources(db) -> None:
    if db.query(Source).filter(Source.id == "src-eval-conflict-official").first():
        return
    now = datetime.now(timezone.utc)
    source_a = Source(
        id="src-eval-conflict-official",
        title="Global Access Policy",
        source_type="markdown",
        mime_type="text/markdown",
        file_path=None,
        url=None,
        uploaded_at=now,
        updated_at=now,
        created_by="eval",
        parse_status="completed",
        ingest_status="completed",
        metadata_json={"authorityLevel": "official", "sourceStatus": "approved", "documentType": "policy"},
        checksum="src-eval-conflict-official",
        trust_level="high",
        file_size=None,
        description="Global policy",
        tags=["policy"],
        collection_id=None,
    )
    source_b = Source(
        id="src-eval-conflict-informal",
        title="Regional Access Note",
        source_type="markdown",
        mime_type="text/markdown",
        file_path=None,
        url=None,
        uploaded_at=now,
        updated_at=now,
        created_by="eval",
        parse_status="completed",
        ingest_status="completed",
        metadata_json={"authorityLevel": "informal", "sourceStatus": "draft", "documentType": "policy"},
        checksum="src-eval-conflict-informal",
        trust_level="medium",
        file_size=None,
        description="Regional note",
        tags=["note"],
        collection_id=None,
    )
    chunk_a = SourceChunk(
        id="chunk-eval-conflict-official",
        source_id=source_a.id,
        chunk_index=0,
        section_title="Policy Rule",
        page_number=1,
        content="Global policy requires CAB approval for production changes affecting more than 5000 users.",
        token_count=13,
        embedding_id=None,
        metadata_json={"sectionRole": "rule"},
        span_start=0,
        span_end=92,
        created_at=now,
    )
    chunk_b = SourceChunk(
        id="chunk-eval-conflict-informal",
        source_id=source_b.id,
        chunk_index=0,
        section_title="Regional Note",
        page_number=1,
        content="Regional note says CAB approval is only needed above 3000 users for one local team.",
        token_count=15,
        embedding_id=None,
        metadata_json={"sectionRole": "rule"},
        span_start=0,
        span_end=84,
        created_at=now,
    )
    db.add_all([source_a, source_b, chunk_a, chunk_b])
    db.commit()


def _seed_planner_source(db) -> None:
    if db.query(Source).filter(Source.id == "src-eval-planner-runbook").first():
        return
    now = datetime.now(timezone.utc)
    source = Source(
        id="src-eval-planner-runbook",
        title="Power Toolkit Demo Runbook",
        source_type="markdown",
        mime_type="text/markdown",
        file_path=None,
        url=None,
        uploaded_at=now,
        updated_at=now,
        created_by="eval",
        parse_status="completed",
        ingest_status="completed",
        metadata_json={"authorityLevel": "official", "sourceStatus": "approved", "documentType": "sop"},
        checksum="src-eval-planner-runbook",
        trust_level="high",
        file_size=None,
        description="Planner eval source",
        tags=["sop", "demo"],
        collection_id=None,
    )
    db.add_all(
        [
            source,
            SourceChunk(
                id="chunk-eval-planner-prep",
                source_id=source.id,
                chunk_index=0,
                section_title="Preparation",
                page_number=1,
                content="Before the Power Toolkit demo, prepare a sample environment, verify credentials, and preload the dataset.",
                token_count=14,
                embedding_id=None,
                metadata_json={"sectionRole": "step"},
                span_start=0,
                span_end=106,
                created_at=now,
            ),
            SourceChunk(
                id="chunk-eval-planner-risk",
                source_id=source.id,
                chunk_index=1,
                section_title="Risk Notes",
                page_number=1,
                content="The main demo risks are stale credentials, missing browser extensions, and inconsistent sample data.",
                token_count=14,
                embedding_id=None,
                metadata_json={"sectionRole": "exception"},
                span_start=107,
                span_end=208,
                created_at=now,
            ),
            SourceChunk(
                id="chunk-eval-planner-test",
                source_id=source.id,
                chunk_index=2,
                section_title="Test First",
                page_number=1,
                content="Test authentication, extension loading, and the first guided scenario before the live handoff.",
                token_count=13,
                embedding_id=None,
                metadata_json={"sectionRole": "step"},
                span_start=209,
                span_end=305,
                created_at=now,
            ),
        ]
    )
    db.commit()


def _seed_notebook_source(db) -> None:
    if db.query(Source).filter(Source.id == "src-eval-notebook-source").first():
        return
    now = datetime.now(timezone.utc)
    source = Source(
        id="src-eval-notebook-source",
        title="Access Approval Runbook",
        source_type="markdown",
        mime_type="text/markdown",
        file_path=None,
        url=None,
        uploaded_at=now,
        updated_at=now,
        created_by="eval",
        parse_status="completed",
        ingest_status="completed",
        metadata_json={
            "authorityLevel": "official",
            "sourceStatus": "approved",
            "documentType": "sop",
            "notebookContext": {
                "documentType": "sop",
                "sourceBrief": "This runbook explains how to approve access requests, validate identity, and escalate privileged access.",
                "keyPoints": [
                    "Validate requester identity before approval.",
                    "Escalate privileged access requests to security.",
                ],
                "notes": [
                    {
                        "id": "note-eval-notebook-step",
                        "kind": "procedure",
                        "title": "Initial validation",
                        "text": "Validate requester identity before any approval action.",
                        "roles": ["step", "summary"],
                        "provenance": {"sourceId": "src-eval-notebook-source", "chunkIds": ["chunk-eval-notebook-step"], "sectionKeys": ["sec-step"]},
                    },
                    {
                        "id": "note-eval-notebook-risk",
                        "kind": "risk",
                        "title": "Privileged access exception",
                        "text": "Escalate privileged access requests to security before final approval.",
                        "roles": ["exception", "risk"],
                        "provenance": {"sourceId": "src-eval-notebook-source", "chunkIds": ["chunk-eval-notebook-risk"], "sectionKeys": ["sec-risk"]},
                    },
                ],
                "recommendedPrompts": [
                    "What should I do first before approving access?",
                    "What exceptions or risks appear in this runbook?",
                    "Which section should I read first in this runbook?",
                ],
            },
        },
        checksum="src-eval-notebook-source",
        trust_level="high",
        file_size=None,
        description="Notebook eval source",
        tags=["sop", "notebook"],
        collection_id=None,
    )
    db.add_all(
        [
            source,
            SourceChunk(
                id="chunk-eval-notebook-step",
                source_id=source.id,
                chunk_index=0,
                section_title="Initial Validation",
                page_number=1,
                content="Validate requester identity before any approval action.",
                token_count=8,
                embedding_id=None,
                metadata_json={"sectionRole": "step"},
                span_start=0,
                span_end=55,
                created_at=now,
            ),
            SourceChunk(
                id="chunk-eval-notebook-risk",
                source_id=source.id,
                chunk_index=1,
                section_title="Privileged Access Exception",
                page_number=1,
                content="Escalate privileged access requests to security before final approval.",
                token_count=10,
                embedding_id=None,
                metadata_json={"sectionRole": "exception"},
                span_start=56,
                span_end=127,
                created_at=now,
            ),
        ]
    )
    db.commit()


def _seed_multimodal_artifact_source(db) -> None:
    if db.query(Source).filter(Source.id == "src-eval-multimodal-artifact").first():
        return
    now = datetime.now(timezone.utc)
    source = Source(
        id="src-eval-multimodal-artifact",
        title="Release Review Artifact Pack",
        source_type="markdown",
        mime_type="text/markdown",
        file_path=None,
        url=None,
        uploaded_at=now,
        updated_at=now,
        created_by="eval",
        parse_status="completed",
        ingest_status="completed",
        metadata_json={
            "authorityLevel": "official",
            "sourceStatus": "approved",
            "documentType": "report",
            "multimodalArtifacts": [
                {
                    "id": "src-eval-multimodal-artifact-notebook",
                    "sourceId": "src-eval-multimodal-artifact",
                    "artifactType": "notebook",
                    "title": "Artifact Checklist",
                    "status": "available",
                    "summary": "Approval checklist artifact highlights banner state, warning count, and reviewer next steps.",
                    "previewText": "Check the approval banner, warning count, and reviewer checklist before release.",
                    "metadataJson": {
                        "recommendedPrompts": [
                            "What evidence should I inspect first in the artifact pack?"
                        ]
                    },
                }
            ],
        },
        checksum="src-eval-multimodal-artifact",
        trust_level="high",
        file_size=None,
        description="Artifact eval source",
        tags=["artifact", "multimodal"],
        collection_id=None,
    )
    db.add_all(
        [
            source,
            SourceChunk(
                id="chunk-eval-multimodal-artifact",
                source_id=source.id,
                chunk_index=0,
                section_title="Approval Checklist",
                page_number=1,
                content="Review the artifact checklist, confirm the approval banner, and verify warning counts before release.",
                token_count=14,
                embedding_id=None,
                metadata_json={"sectionRole": "rule"},
                span_start=0,
                span_end=103,
                created_at=now,
            ),
        ]
    )
    db.commit()


def evaluate(selected_tags: list[str] | None = None) -> dict:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)
        _seed_conflict_sources(db)
        _seed_planner_source(db)
        _seed_notebook_source(db)
        _seed_multimodal_artifact_source(db)
        selected_tags = [tag.strip() for tag in (selected_tags or []) if tag.strip()]
        content_cases = _filter_cases_by_tags(dataset["cases"], selected_tags)
        behavior_dataset_cases = _filter_cases_by_tags(dataset.get("behaviorCases", []), selected_tags)
        cases = []
        for case in content_cases:
            answer = ask(db, case["query"])
            results = search(db, case["query"], limit=5)
            answer_text = f"{answer['answer']} {' '.join(citation.get('snippet', '') for citation in answer['citations'])}"
            expected_hits = _term_hits(answer_text, case["expectedTerms"])
            citation_source_ids = {citation["sourceId"] for citation in answer["citations"]}
            source_hit = bool(citation_source_ids & set(case["expectedSourceIds"]))
            diagnostics = answer.get("diagnostics", {})
            top_score = diagnostics.get("topChunks", [{}])[0].get("finalScore", 0) if diagnostics.get("topChunks") else 0
            confidence = calibrate_confidence(top_score, len(answer["citations"]), len(case["expectedTerms"]), len(citation_source_ids))
            top_candidate_source_ids = _candidate_source_ids(answer, limit=10)
            retrieval_recall_at_5 = _recall_at_k(top_candidate_source_ids, case["expectedSourceIds"], 5)
            retrieval_recall_at_10 = _recall_at_k(top_candidate_source_ids, case["expectedSourceIds"], 10)
            rerank_precision_at_5 = _precision_at_k(top_candidate_source_ids, case["expectedSourceIds"], 5)
            citation_precision = round(
                sum(1 for source_id in answer["citations"] if source_id.get("sourceId") in set(case["expectedSourceIds"]))
                / max(len(answer["citations"]), 1),
                4,
            )
            answer_faithfulness = round(
                min(
                    1.0,
                    (expected_hits / max(len(case["expectedTerms"]), 1)) * 0.6
                    + (1.0 if source_hit else 0.0) * 0.25
                    + min(len(answer["citations"]) / max(len(case["expectedTerms"]), 1), 1.0) * 0.15,
                ),
                4,
            )
            cases.append(
                {
                    "id": case["id"],
                    "query": case["query"],
                    "retrievalHitRate": 1.0 if results else 0.0,
                    "retrievalRecallAt5": retrieval_recall_at_5,
                    "retrievalRecallAt10": retrieval_recall_at_10,
                    "rerankPrecisionAt5": rerank_precision_at_5,
                    "citationCoverage": round(expected_hits / max(len(case["expectedTerms"]), 1), 4),
                    "citationPrecision": citation_precision,
                    "answerFaithfulness": answer_faithfulness,
                    "expectedSourceHit": source_hit,
                    "unsupportedClaimCount": 0 if expected_hits else 1,
                    "calibratedConfidence": confidence.calibrated,
                    "citationCount": len(answer["citations"]),
                    "tags": case.get("tags", []),
                }
            )

        behavior_cases = []
        for case in behavior_dataset_cases:
            if case["type"] in {"clarification", "followup_resolution"}:
                first = ask(db, case["initialQuery"])
                answer = ask(db, case["followupQuery"], session_id=first["sessionId"])
            elif case["type"] in {"scoped_ask", "notebook_summary", "suggestion_usefulness"}:
                answer = ask(db, case["query"], source_id=case.get("sourceId"))
            else:
                answer = ask(db, case["query"])
            diagnostics = answer.get("diagnostics", {})
            selected_context = diagnostics.get("selectedContext") or []
            citation_source_ids = {citation["sourceId"] for citation in answer.get("citations", []) if citation.get("sourceId")}
            answer_text = f"{answer['answer']} {' '.join(citation.get('snippet', '') for citation in answer.get('citations', []))}"

            result = {
                "id": case["id"],
                "type": case["type"],
                "answerType": answer.get("answerType"),
                "success": False,
                "tags": case.get("tags", []),
                "citations": answer.get("citations", []),
                "relatedPages": answer.get("relatedPages", []),
                "relatedSources": answer.get("relatedSources", []),
            }

            if case["type"] == "clarification":
                result["success"] = (
                    answer.get("answerType") == case["expectedAnswerType"]
                    and diagnostics.get("clarificationTriggered") is True
                )
            elif case["type"] == "followup_resolution":
                expected_hits = _term_hits(answer_text, case.get("expectedTerms", []))
                source_hit = bool(citation_source_ids & set(case.get("expectedSourceIds", [])))
                standalone_query = (answer.get("interpretedQuery") or {}).get("standaloneQuery") or ""
                result.update(
                    {
                        "termCoverage": round(expected_hits / max(len(case.get("expectedTerms", [])), 1), 4),
                        "expectedSourceHit": source_hit,
                        "standaloneQuery": standalone_query,
                    }
                )
                result["success"] = (
                    answer.get("answerType") == case["expectedAnswerType"]
                    and source_hit
                    and expected_hits >= max(1, len(case.get("expectedTerms", [])) - 1)
                    and standalone_query != case["followupQuery"]
                )
            elif case["type"] == "source_lookup":
                source_hit = bool(citation_source_ids & set(case.get("expectedSourceIds", [])))
                result["expectedSourceHit"] = source_hit
                result["success"] = answer.get("answerType") == case["expectedAnswerType"] and source_hit
            elif case["type"] == "conflict":
                conflicts = answer.get("conflicts") or []
                preferred = (conflicts or [{}])[0].get("preferredSourceTitle")
                roles = [item.get("role") for item in selected_context]
                result.update({"preferredSourceTitle": preferred, "roles": roles})
                result["success"] = (
                    answer.get("answerType") == case["expectedAnswerType"]
                    and preferred == case["expectedPreferredSourceTitle"]
                    and all(role in roles for role in case.get("expectedRoles", []))
                )
            elif case["type"] == "analysis_planning":
                planner = (answer.get("interpretedQuery") or {}).get("planner") or {}
                subqueries = planner.get("subQueries") or []
                planner_intents = [item.get("intent") for item in subqueries]
                roles = [item.get("role") for item in selected_context]
                result.update(
                    {
                        "plannerStrategy": planner.get("strategy"),
                        "plannerIntents": planner_intents,
                        "roles": roles,
                    }
                )
                result["success"] = (
                    answer.get("answerType") == case["expectedAnswerType"]
                    and planner.get("strategy") == case["expectedPlannerStrategy"]
                    and all(intent in planner_intents for intent in case.get("expectedPlannerIntents", []))
                    and "step" in roles
                    and "exception" in roles
                )
            elif case["type"] == "scoped_ask":
                top_candidates = diagnostics.get("topCandidates") or []
                scope = answer.get("scope") or {}
                result.update(
                    {
                        "scopeId": scope.get("id"),
                        "answerType": answer.get("answerType"),
                        "topCandidateTypes": [item.get("candidateType") for item in top_candidates[:5]],
                    }
                )
                result["success"] = (
                    scope.get("id") == case["expectedScopeId"]
                    and case["expectedTopCandidateType"] in result["topCandidateTypes"]
                )
            elif case["type"] == "notebook_summary":
                expected_hits = _term_hits(answer_text, case.get("expectedTerms", []))
                top_candidates = diagnostics.get("topCandidates") or []
                result.update(
                    {
                        "answerType": answer.get("answerType"),
                        "termCoverage": round(expected_hits / max(len(case.get("expectedTerms", [])), 1), 4),
                        "topCandidateTypes": [item.get("candidateType") for item in top_candidates[:5]],
                    }
                )
                result["success"] = (
                    expected_hits >= max(1, len(case.get("expectedTerms", [])) - 1)
                    and case["expectedTopCandidateType"] in result["topCandidateTypes"]
                )
            elif case["type"] == "authority_synthesis":
                conflicts = answer.get("conflicts") or []
                preferred = (conflicts or [{}])[0].get("preferredSourceTitle")
                result.update(
                    {
                        "preferredSourceTitle": preferred,
                        "answerSections": [section for section in case.get("expectedAnswerSections", []) if section in answer.get("answer", "")],
                    }
                )
                result["success"] = (
                    answer.get("answerType") == case["expectedAnswerType"]
                    and preferred == case["expectedPreferredSourceTitle"]
                    and len(result["answerSections"]) == len(case.get("expectedAnswerSections", []))
                )
            elif case["type"] == "suggestion_usefulness":
                prompts = answer.get("suggestedPrompts") or []
                categories = [item.get("category") for item in prompts]
                result.update({"promptCount": len(prompts), "categories": categories})
                result["success"] = (
                    len(prompts) >= int(case.get("minimumPromptCount", 1))
                    and all(category in categories for category in case.get("expectedCategories", []))
                )
            behavior_cases.append(result)

        unsupported_answer = ask(db, dataset["syntheticCases"]["unsupportedClaim"])
        unsupported_count = 0 if unsupported_answer["citations"] else 1
        lint_report = run_lint(db, page_size=100, max_pages=100)
        page_type_markdown = build_page_markdown(
            "Phase 17 SOP Check",
            "A test SOP page.",
            [{"section_title": "Procedure", "content": "Step 1: Prepare. Step 2: Validate. Step 3: Publish.", "token_count": 9}],
            ["Procedure has ordered steps."],
            page_type="sop",
        )
        fallback_summary, fallback_facts = summarize_text("Invalid JSON Fallback", "This sentence is long enough to become a fallback fact. Another sentence confirms the fallback path remains stable.")
        invalid_json_guard = False
        try:
            json_like_to_dict("not json")
        except ValueError:
            invalid_json_guard = True

        report = {
            "success": True,
            "version": EVAL_VERSION,
            "requestedTags": selected_tags,
            "caseCount": len(cases),
            "cases": cases,
            "behaviorCaseCount": len(behavior_cases),
            "behaviorCases": behavior_cases,
            "averages": {
                "citationCoverage": round(sum(item["citationCoverage"] for item in cases) / max(len(cases), 1), 4),
                "citationPrecision": round(sum(item["citationPrecision"] for item in cases) / max(len(cases), 1), 4),
                "retrievalHitRate": round(sum(item["retrievalHitRate"] for item in cases) / max(len(cases), 1), 4),
                "retrievalRecallAt5": round(sum(item["retrievalRecallAt5"] for item in cases) / max(len(cases), 1), 4),
                "retrievalRecallAt10": round(sum(item["retrievalRecallAt10"] for item in cases) / max(len(cases), 1), 4),
                "rerankPrecisionAt5": round(sum(item["rerankPrecisionAt5"] for item in cases) / max(len(cases), 1), 4),
                "answerFaithfulness": round(sum(item["answerFaithfulness"] for item in cases) / max(len(cases), 1), 4),
                "unsupportedClaimCount": unsupported_count,
            },
            "behaviorMetrics": {
                "clarificationAccuracy": round(
                    sum(1 for item in behavior_cases if item["type"] == "clarification" and item["success"])
                    / max(sum(1 for item in behavior_cases if item["type"] == "clarification"), 1),
                    4,
                ),
                "followupResolutionSuccess": round(
                    sum(1 for item in behavior_cases if item["type"] == "followup_resolution" and item["success"])
                    / max(sum(1 for item in behavior_cases if item["type"] == "followup_resolution"), 1),
                    4,
                ),
                "sourceLookupAccuracy": round(
                    sum(1 for item in behavior_cases if item["type"] == "source_lookup" and item["success"])
                    / max(sum(1 for item in behavior_cases if item["type"] == "source_lookup"), 1),
                    4,
                ),
                "conflictHandlingAccuracy": round(
                    sum(1 for item in behavior_cases if item["type"] == "conflict" and item["success"])
                    / max(sum(1 for item in behavior_cases if item["type"] == "conflict"), 1),
                    4,
                ),
                "analysisPlanningAccuracy": round(
                    sum(1 for item in behavior_cases if item["type"] == "analysis_planning" and item["success"])
                    / max(sum(1 for item in behavior_cases if item["type"] == "analysis_planning"), 1),
                    4,
                ),
                "scopeAdherence": round(
                    sum(1 for item in behavior_cases if item["type"] == "scoped_ask" and item["success"])
                    / max(sum(1 for item in behavior_cases if item["type"] == "scoped_ask"), 1),
                    4,
                ),
                "notebookSummaryAccuracy": round(
                    sum(1 for item in behavior_cases if item["type"] == "notebook_summary" and item["success"])
                    / max(sum(1 for item in behavior_cases if item["type"] == "notebook_summary"), 1),
                    4,
                ),
                "authoritySynthesisAccuracy": round(
                    sum(1 for item in behavior_cases if item["type"] == "authority_synthesis" and item["success"])
                    / max(sum(1 for item in behavior_cases if item["type"] == "authority_synthesis"), 1),
                    4,
                ),
                "suggestionUsefulnessProxy": round(
                    sum(1 for item in behavior_cases if item["type"] == "suggestion_usefulness" and item["success"])
                    / max(sum(1 for item in behavior_cases if item["type"] == "suggestion_usefulness"), 1),
                    4,
                ),
            },
            "synthetic": {
                "conflictRuleAvailable": "conflicting_pages" in lint_report["summary"]["byRule"] or "conflicting_pages" in {rule["id"] for rule in lint_report["summary"]["rules"]},
                "staleRuleAvailable": "stale_authoritative_source" in {rule["id"] for rule in lint_report["summary"]["rules"]},
                "authorityMismatchRuleAvailable": "authority_mismatch_sources" in {rule["id"] for rule in lint_report["summary"]["rules"]},
                "archivedSourceRuleAvailable": "archived_source_link" in {rule["id"] for rule in lint_report["summary"]["rules"]},
                "sopHasSteps": "## Procedure" in page_type_markdown and "Step 1" in page_type_markdown,
                "invalidJsonGuard": invalid_json_guard,
                "fallbackSummaryOk": bool(fallback_summary and fallback_facts),
            },
            "reviewReasonTaxonomy": REVIEW_REASON_TAXONOMY,
        }
        has_content_cases = len(cases) > 0
        behavior_counts = {
            "clarification": sum(1 for item in behavior_cases if item["type"] == "clarification"),
            "followup_resolution": sum(1 for item in behavior_cases if item["type"] == "followup_resolution"),
            "source_lookup": sum(1 for item in behavior_cases if item["type"] == "source_lookup"),
            "conflict": sum(1 for item in behavior_cases if item["type"] == "conflict"),
            "analysis_planning": sum(1 for item in behavior_cases if item["type"] == "analysis_planning"),
            "scoped_ask": sum(1 for item in behavior_cases if item["type"] == "scoped_ask"),
            "notebook_summary": sum(1 for item in behavior_cases if item["type"] == "notebook_summary"),
            "authority_synthesis": sum(1 for item in behavior_cases if item["type"] == "authority_synthesis"),
            "suggestion_usefulness": sum(1 for item in behavior_cases if item["type"] == "suggestion_usefulness"),
        }
        report["qualityGates"] = {
            "retrievalHitRate": (not has_content_cases) or report["averages"]["retrievalHitRate"] >= 1.0,
            "citationCoverage": (not has_content_cases) or report["averages"]["citationCoverage"] >= 0.5,
            "citationPrecision": (not has_content_cases) or report["averages"]["citationPrecision"] >= 0.9,
            "retrievalRecallAt5": (not has_content_cases) or report["averages"]["retrievalRecallAt5"] >= 0.66,
            "retrievalRecallAt10": (not has_content_cases) or report["averages"]["retrievalRecallAt10"] >= 0.66,
            "rerankPrecisionAt5": (not has_content_cases) or report["averages"]["rerankPrecisionAt5"] >= 0.5,
            "answerFaithfulness": (not has_content_cases) or report["averages"]["answerFaithfulness"] >= 0.7,
            "clarificationAccuracy": (behavior_counts["clarification"] == 0) or report["behaviorMetrics"]["clarificationAccuracy"] >= 1.0,
            "followupResolutionSuccess": (behavior_counts["followup_resolution"] == 0) or report["behaviorMetrics"]["followupResolutionSuccess"] >= 1.0,
            "sourceLookupAccuracy": (behavior_counts["source_lookup"] == 0) or report["behaviorMetrics"]["sourceLookupAccuracy"] >= 1.0,
            "conflictHandlingAccuracy": (behavior_counts["conflict"] == 0) or report["behaviorMetrics"]["conflictHandlingAccuracy"] >= 1.0,
            "analysisPlanningAccuracy": (behavior_counts["analysis_planning"] == 0) or report["behaviorMetrics"]["analysisPlanningAccuracy"] >= 1.0,
            "scopeAdherence": (behavior_counts["scoped_ask"] == 0) or report["behaviorMetrics"]["scopeAdherence"] >= 1.0,
            "notebookSummaryAccuracy": (behavior_counts["notebook_summary"] == 0) or report["behaviorMetrics"]["notebookSummaryAccuracy"] >= 1.0,
            "authoritySynthesisAccuracy": (behavior_counts["authority_synthesis"] == 0) or report["behaviorMetrics"]["authoritySynthesisAccuracy"] >= 1.0,
            "suggestionUsefulnessProxy": (behavior_counts["suggestion_usefulness"] == 0) or report["behaviorMetrics"]["suggestionUsefulnessProxy"] >= 1.0,
            "invalidJsonGuard": report["synthetic"]["invalidJsonGuard"],
            "sopHasSteps": report["synthetic"]["sopHasSteps"],
            "authorityMismatchRuleAvailable": report["synthetic"]["authorityMismatchRuleAvailable"],
            "archivedSourceRuleAvailable": report["synthetic"]["archivedSourceRuleAvailable"],
        }
        report["qualityGates"]["allPassed"] = all(report["qualityGates"].values())
        report["success"] = (
            report["qualityGates"]["allPassed"]
        )
        create_eval_run(
            db,
            run_type="eval",
            run_name="ask-ai-quality-eval",
            version=report["version"],
            report=report,
            tags=["ask-ai", "quality", "phase4", *selected_tags],
        )
        return report
    finally:
        db.close()


def write_reports(report: dict) -> None:
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        f"# Quality Eval Report ({report['version']})",
        "",
        f"- Success: {report['success']}",
        f"- Requested tags: {', '.join(report.get('requestedTags') or []) or 'all'}",
        f"- Cases: {report['caseCount']}",
        f"- Citation coverage: {report['averages']['citationCoverage']}",
        f"- Citation precision: {report['averages']['citationPrecision']}",
        f"- Retrieval hit rate: {report['averages']['retrievalHitRate']}",
        f"- Retrieval recall@5: {report['averages']['retrievalRecallAt5']}",
        f"- Retrieval recall@10: {report['averages']['retrievalRecallAt10']}",
        f"- Rerank precision@5: {report['averages']['rerankPrecisionAt5']}",
        f"- Answer faithfulness: {report['averages']['answerFaithfulness']}",
        f"- Unsupported claim count: {report['averages']['unsupportedClaimCount']}",
        f"- Clarification accuracy: {report['behaviorMetrics']['clarificationAccuracy']}",
        f"- Follow-up resolution: {report['behaviorMetrics']['followupResolutionSuccess']}",
        f"- Source lookup accuracy: {report['behaviorMetrics']['sourceLookupAccuracy']}",
        f"- Conflict handling accuracy: {report['behaviorMetrics']['conflictHandlingAccuracy']}",
        f"- Analysis planning accuracy: {report['behaviorMetrics']['analysisPlanningAccuracy']}",
        f"- Scope adherence: {report['behaviorMetrics']['scopeAdherence']}",
        f"- Notebook summary accuracy: {report['behaviorMetrics']['notebookSummaryAccuracy']}",
        f"- Authority synthesis accuracy: {report['behaviorMetrics']['authoritySynthesisAccuracy']}",
        f"- Suggestion usefulness proxy: {report['behaviorMetrics']['suggestionUsefulnessProxy']}",
        "",
        "## Cases",
    ]
    for case in report["cases"]:
        lines.append(
            f"- `{case['id']}` recall@5={case['retrievalRecallAt5']} precision@5={case['rerankPrecisionAt5']} "
            f"faithfulness={case['answerFaithfulness']} sourceHit={case['expectedSourceHit']} confidence={case['calibratedConfidence']}"
        )
    lines.extend(["", "## Behavior Cases"])
    for case in report["behaviorCases"]:
        lines.append(f"- `{case['id']}` type={case['type']} success={case['success']} answerType={case['answerType']}")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Ask AI quality eval suite.")
    parser.add_argument("--tag", dest="tags", action="append", default=[], help="Run only cases matching a tag. Repeatable.")
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    report = evaluate(selected_tags=args.tags)
    write_reports(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
