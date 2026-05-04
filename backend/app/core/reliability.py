from __future__ import annotations

from dataclasses import dataclass


PROMPT_VERSION = "wiki-ingest-v2.1"
EVAL_VERSION = "phase17-eval-v1"

REVIEW_REASON_TAXONOMY = {
    "unsupported_claim": "Claim is not backed by retrieved source evidence.",
    "citation_gap": "Important generated content lacks chunk-level citation.",
    "conflict": "Source or page content appears contradictory.",
    "stale_source": "Authoritative source evidence is older than freshness threshold.",
    "format_quality": "Generated page does not meet page-type structure expectations.",
    "llm_failure": "Provider output was missing, malformed, or could not be parsed.",
}


@dataclass(frozen=True)
class ConfidenceBreakdown:
    retrieval: float
    citation_coverage: float
    source_trust: float

    @property
    def calibrated(self) -> float:
        return round(max(0.0, min((self.retrieval * 0.5) + (self.citation_coverage * 0.3) + (self.source_trust * 0.2), 1.0)), 4)


def calibrate_confidence(retrieval_score: float, citation_count: int, expected_citations: int, trusted_source_count: int) -> ConfidenceBreakdown:
    citation_coverage = min(citation_count / max(expected_citations, 1), 1.0)
    source_trust = min(trusted_source_count / max(citation_count, 1), 1.0) if citation_count else 0.0
    return ConfidenceBreakdown(
        retrieval=max(0.0, min(retrieval_score, 1.0)),
        citation_coverage=citation_coverage,
        source_trust=source_trust,
    )

