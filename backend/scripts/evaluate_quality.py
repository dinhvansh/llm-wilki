from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "evals" / "golden_dataset.json"
REPORT_JSON = ROOT / "evals" / "last_eval_report.json"
REPORT_MD = ROOT / "evals" / "last_eval_report.md"

os.environ.setdefault("DATABASE_URL", f"sqlite:///{(ROOT / 'quality_eval.db').as_posix()}")
os.environ.setdefault("AUTO_SEED_DEMO_DATA", "true")
os.environ.setdefault("JOB_QUEUE_BACKEND", "database")
os.environ.setdefault("DEBUG", "true")
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.core.ingest import build_page_markdown, json_like_to_dict, summarize_text  # noqa: E402
from app.core.reliability import EVAL_VERSION, REVIEW_REASON_TAXONOMY, calibrate_confidence  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.services.lint import run_lint  # noqa: E402
from app.services.query import ask, search  # noqa: E402


def _term_hits(text: str, terms: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if term.lower() in lowered)


def evaluate() -> dict:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)
        cases = []
        for case in dataset["cases"]:
            answer = ask(db, case["query"])
            results = search(db, case["query"], limit=5)
            answer_text = f"{answer['answer']} {' '.join(citation.get('snippet', '') for citation in answer['citations'])}"
            expected_hits = _term_hits(answer_text, case["expectedTerms"])
            citation_source_ids = {citation["sourceId"] for citation in answer["citations"]}
            source_hit = bool(citation_source_ids & set(case["expectedSourceIds"]))
            diagnostics = answer.get("diagnostics", {})
            top_score = diagnostics.get("topChunks", [{}])[0].get("finalScore", 0) if diagnostics.get("topChunks") else 0
            confidence = calibrate_confidence(top_score, len(answer["citations"]), len(case["expectedTerms"]), len(citation_source_ids))
            cases.append(
                {
                    "id": case["id"],
                    "query": case["query"],
                    "retrievalHitRate": 1.0 if results else 0.0,
                    "citationCoverage": round(expected_hits / max(len(case["expectedTerms"]), 1), 4),
                    "expectedSourceHit": source_hit,
                    "unsupportedClaimCount": 0 if expected_hits else 1,
                    "calibratedConfidence": confidence.calibrated,
                    "citationCount": len(answer["citations"]),
                }
            )

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
            "caseCount": len(cases),
            "cases": cases,
            "averages": {
                "citationCoverage": round(sum(item["citationCoverage"] for item in cases) / max(len(cases), 1), 4),
                "retrievalHitRate": round(sum(item["retrievalHitRate"] for item in cases) / max(len(cases), 1), 4),
                "unsupportedClaimCount": unsupported_count,
            },
            "synthetic": {
                "conflictRuleAvailable": "conflicting_pages" in lint_report["summary"]["byRule"] or "conflicting_pages" in {rule["id"] for rule in lint_report["summary"]["rules"]},
                "staleRuleAvailable": "stale_authoritative_source" in {rule["id"] for rule in lint_report["summary"]["rules"]},
                "sopHasSteps": "## Procedure" in page_type_markdown and "Step 1" in page_type_markdown,
                "invalidJsonGuard": invalid_json_guard,
                "fallbackSummaryOk": bool(fallback_summary and fallback_facts),
            },
            "reviewReasonTaxonomy": REVIEW_REASON_TAXONOMY,
        }
        report["success"] = (
            report["averages"]["citationCoverage"] >= 0.5
            and report["averages"]["retrievalHitRate"] >= 1.0
            and report["synthetic"]["invalidJsonGuard"]
            and report["synthetic"]["sopHasSteps"]
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
        f"- Cases: {report['caseCount']}",
        f"- Citation coverage: {report['averages']['citationCoverage']}",
        f"- Retrieval hit rate: {report['averages']['retrievalHitRate']}",
        f"- Unsupported claim count: {report['averages']['unsupportedClaimCount']}",
        "",
        "## Cases",
    ]
    for case in report["cases"]:
        lines.append(f"- `{case['id']}` coverage={case['citationCoverage']} sourceHit={case['expectedSourceHit']} confidence={case['calibratedConfidence']}")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    report = evaluate()
    write_reports(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

