# RAG Answer Policy Upgrade Plan

Date: 2026-05-15

## Goal

Upgrade Ask AI so official answers are grounded in indexed knowledge-base evidence, support cross-lingual questions, and fail safely when evidence is missing or weak.

The target behavior is:

- no evidence -> no official answer
- weak evidence -> partial answer or no-answer
- user language controls answer language
- source language remains authoritative
- every final answer exposes evidence status, citations, and verification diagnostics

## Current State

The project already has several useful building blocks:

- `backend/app/services/query.py` performs Ask retrieval, context assembly, answer generation, citations, related pages/sources, and diagnostics.
- `backend/app/services/evidence_policy.py` grades candidate evidence with term coverage, specificity, authority, freshness, and contradiction risk.
- `backend/app/services/answer_verifier.py` runs a deterministic support check over selected candidates and citations.
- `backend/app/schemas/query.py` already exposes `diagnostics.answerVerification` and retrieval diagnostics.
- `llm-wiki/src/app/(main)/ask/page.tsx` already renders citation cards, confidence, retrieval fallback state, evidence verification, and debug diagnostics.

Main gaps:

- no first-class `answerMode` contract: answer, partial answer, no-answer, general-knowledge fallback
- no explicit retrieval quality gate object before generation
- no cross-lingual query rewrite contract
- no strict block that prevents a weak generated answer from being returned as a normal answer
- no clear UI state for no-answer and partial-answer modes
- no regression tests for missing-data and cross-language cases

## Product Policy

### Official Answer Rules

- Ask AI must answer only from indexed knowledge-base context.
- If context is insufficient, Ask AI must say the knowledge base does not contain enough evidence.
- Ask AI must not use outside knowledge for official answers.
- If general knowledge fallback is later allowed, it must be an explicit opt-in mode and visually labeled as non-official.
- Citations must point to the original source language and source artifact.

### No-Answer Copy

Default no-answer:

```text
I could not find enough relevant evidence in the current knowledge base to answer this accurately. Upload a related source, narrow the question, or expand the search scope.
```

Vietnamese no-answer:

```text
Toi chua tim thay du bang chung lien quan trong knowledge base de tra loi chinh xac. Ban co the upload them tai lieu lien quan, hoi cu the hon, hoac mo rong pham vi tim kiem.
```

Partial answer:

```text
I found evidence for part of the question, but not enough to answer everything. The answer below only covers the supported portion.
```

Vietnamese partial answer:

```text
Toi chi tim thay bang chung cho mot phan cau hoi. Cau tra loi duoi day chi bao gom phan co nguon ho tro.
```

## Target Flow

```text
User question
-> detect user language
-> build standalone query
-> cross-lingual query rewrite when useful
-> retrieve with original + rewritten queries
-> rerank
-> retrieval quality gate
-> no-answer if evidence is insufficient
-> context assembly
-> draft answer
-> answer verifier
-> final answer mode decision
-> response with citations, diagnostics, and UI status
```

## Response Contract

Add these fields to Ask response:

```json
{
  "answerMode": "answer | partial_answer | no_answer | general_fallback",
  "answerLanguage": "vi",
  "sourceLanguages": ["en"],
  "evidenceStatus": "supported | partial | insufficient | unsupported",
  "evidenceGate": {
    "passed": true,
    "reason": "sufficient_evidence",
    "topScore": 0.82,
    "coverage": 0.71,
    "selectedCount": 3,
    "citationCount": 2,
    "warnings": []
  }
}
```

Keep existing fields:

- `answer`
- `citations`
- `confidence`
- `uncertainty`
- `diagnostics.answerVerification`
- `diagnostics.contextCoverage`
- `diagnostics.answerGeneration`

## Phase 1 - Policy Contract

Checklist:

- [x] Add backend enum-style constants for answer modes.
- [x] Add backend enum-style constants for evidence status.
- [x] Extend `AskResponseOut` in `backend/app/schemas/query.py`.
- [x] Extend frontend `AskResponse` type in `llm-wiki/src/lib/types/index.ts`.
- [x] Preserve backward compatibility for old chat message `response_json` records without the new fields.
- [x] Add no-answer and partial-answer default copy helpers.
- [x] Add response fixtures in mock Ask service.

Acceptance:

- [x] Existing Ask response still loads old saved sessions.
- [x] Frontend build passes.
- [x] API schema returns new fields for new Ask responses.

## Phase 2 - Retrieval Quality Gate

Create a dedicated service, for example:

```text
backend/app/services/retrieval_quality_gate.py
```

Inputs:

- user question
- interpreted query
- reranked candidates
- selected candidates
- context coverage
- scope summary

Signals:

- selected count
- citation candidate count
- top candidate score
- max query-term coverage
- average evidence grade
- source authority / freshness
- scope match
- contradiction risk
- intent-specific minimums

Checklist:

- [x] Implement `evaluate_retrieval_quality(...)`.
- [x] Return structured gate result with `passed`, `status`, `reason`, `warnings`, `topScore`, `coverage`, `selectedCount`.
- [x] Tune thresholds per intent:
  - fact / definition: stricter
  - summary / analysis: slightly lower coverage allowed
  - scoped source/page: lower term coverage allowed when scope is explicit
  - conflict / comparison: require multiple sources when possible
- [x] Replace the current hard clear of `selected_candidates` with a gate decision.
- [x] If gate fails before generation, return `answerMode = no_answer`.
- [x] If gate is weak but usable, return `answerMode = partial_answer`.

Acceptance:

- [x] Empty knowledge base returns no-answer.
- [x] Unrelated question returns no-answer even if random chunks exist.
- [x] Scoped source with relevant evidence still answers.
- [x] Low coverage diagnostics are visible in response.

## Phase 3 - Cross-Lingual Query Handling

Add language and rewrite metadata without making translation mandatory for every query.

Checklist:

- [x] Add lightweight language detection for user question.
- [x] Add `answerLanguage` to interpreted query and response.
- [x] Add source language hints where available:
  - source metadata
  - document language from extraction if present
  - fallback heuristic over chunk text
- [x] Add query rewrite variants:
  - original standalone query
  - English rewrite when user language is Vietnamese and corpus appears English-heavy
  - Vietnamese rewrite when useful for Vietnamese corpus
- [x] Search with multiple query variants.
- [x] Deduplicate candidates across variants.
- [x] Track which query variant found each candidate in diagnostics.
- [x] Ensure answer prompt says: answer in the user's language, cite original source.

Acceptance:

- [x] Vietnamese question can retrieve English evidence for an English policy source.
- [x] Answer is Vietnamese when question is Vietnamese.
- [x] Citation snippet remains from the original English source.
- [x] Diagnostics show query variants used.

## Phase 4 - Answer Generation Policy

Current prompt already says to use only evidence and not invent facts. This phase makes the behavior enforceable.

Checklist:

- [x] Split answer generation into explicit modes:
  - no evidence: no LLM answer generation
  - partial evidence: constrained partial answer
  - sufficient evidence: normal grounded answer
- [x] Add prompt variables:
  - answer language
  - answer mode
  - evidence status
  - source language warning
- [x] For cross-lingual answers, require the model to translate only supported evidence.
- [x] For partial answers, require "unsupported parts" section.
- [x] For no-answer, return deterministic copy and skip LLM answer drafting.
- [x] Keep deterministic fallback only as grounded formatting, not as a hallucination path.

Acceptance:

- [x] No selected candidates never produces a normal answer.
- [x] No-answer response has zero or diagnostic-only citations.
- [x] Partial answer explicitly states missing evidence.
- [x] LLM prompt includes answer language and no-outside-knowledge rules.

## Phase 5 - Answer Verifier Gate

Strengthen `backend/app/services/answer_verifier.py`.

Checklist:

- [x] Return `finalDecision`: `answer`, `partial_answer`, `no_answer`.
- [x] Return `coverage`: `full`, `partial`, `none`.
- [x] Return `risk`: `low`, `medium`, `high`.
- [x] Return `unsupportedClaims`.
- [x] Return `missingEvidence`.
- [x] Add deterministic checks:
  - no citation -> no official answer
  - low term coverage -> partial or no-answer
  - answer/evidence overlap very low -> high risk
  - answer contains numbers/dates not in evidence -> high risk warning
- [x] Add optional LLM verifier later behind task profile `review_assist` or new `answer_verifier`.
- [x] If verifier rejects the draft, replace answer with no-answer or partial-answer copy.

Acceptance:

- [x] Unsupported generated draft cannot be returned as normal answer.
- [x] Verification decision is visible in diagnostics.
- [x] Saved chat history stores the final decision.

## Phase 6 - Frontend UX

Update `llm-wiki/src/app/(main)/ask/page.tsx`.

Checklist:

- [x] Add answer mode banner:
  - supported answer
  - partial answer
  - insufficient evidence
  - unsupported answer blocked
- [x] Change "Retrieval fallback" label into clearer `Answer mode`.
- [x] Show evidence gate reason near the answer.
- [x] For cross-lingual answers, show:
  - answer language
  - source language
  - "Source excerpt is shown in original language"
- [x] Keep citations visible for supported and partial answers.
- [x] For no-answer, show suggested actions:
  - upload source
  - broaden scope
  - ask a narrower question
  - inspect top weak matches in debug mode
- [x] Avoid showing confidence as if no-answer was a weak answer.

Acceptance:

- [x] User can distinguish supported, partial, and no-answer responses at a glance.
- [x] No-answer state does not look like a failed request.
- [x] Cross-language citation behavior is clear.

## Phase 7 - Settings

Expose policy knobs without making users tune too much.

Checklist:

- [x] Add advanced Ask settings:
  - minimum top score
  - minimum term coverage
  - allow partial answers
  - allow general fallback, default false
  - cross-lingual rewrite enabled, default true
- [x] Store settings in `RuntimeConfig`.
- [x] Add sane defaults.
- [x] Keep dangerous options clearly labeled.

Recommended defaults:

```text
allowPartialAnswers = true
allowGeneralFallback = false
crossLingualRewriteEnabled = true
minimumTermCoverage = 0.35
minimumTopScore = model-dependent, start with current score distribution
```

Acceptance:

- [x] Settings page can update policy values.
- [x] Existing runtime settings records migrate safely.
- [x] Defaults protect enterprise answers from hallucination.

## Phase 8 - Tests And Evaluation

Backend tests:

- [x] empty DB Ask returns no-answer
- [x] unrelated query with unrelated chunks returns no-answer
- [x] relevant query returns supported answer
- [x] partial evidence returns partial answer
- [x] scoped source missing evidence returns scoped no-answer
- [x] Vietnamese question over English source returns Vietnamese answer with English citation
- [x] answer verifier blocks unsupported numeric/date claims
- [x] old chat session response JSON still deserializes in frontend

Frontend tests:

- [x] Ask page renders supported answer banner
- [x] Ask page renders no-answer banner
- [x] Ask page renders partial-answer banner
- [x] citations remain usable for cross-language answer

E2E smoke:

- [x] ingest English source
- [x] ask Vietnamese question
- [x] verify answer language is Vietnamese
- [x] verify citation source is English
- [x] ask unrelated question
- [x] verify no-answer state

Evaluation cases:

- [x] company policy not in corpus
- [x] policy year mismatch: 2026 asked, only 2024/2025 exists
- [x] English refund policy, Vietnamese question
- [x] source conflict between old and new policy
- [x] exact source-scoped question
- [x] broad summary question

## Phase 9 - Rollout

Checklist:

- [x] Implement feature behind default-on safe policy.
- [x] Run backend compile.
- [x] Run frontend build.
- [x] Run Docker smoke.
- [x] Run E2E smoke.
- [x] Run Ask-specific eval cases.
- [x] Review existing saved conversations for backward compatibility.
- [x] Document behavior in README or product docs.
- [ ] Commit in separate changes:
  - policy contract
  - backend gate/verifier
  - frontend UI
  - tests/evals

## Suggested Implementation Order

1. Add response contract fields and frontend types.
2. Add deterministic no-answer helper.
3. Add retrieval quality gate and wire it before answer generation.
4. Upgrade verifier to produce final decision.
5. Update Ask UI banners and no-answer state.
6. Add cross-lingual query rewrite.
7. Add settings knobs.
8. Add tests and eval cases.
9. Rebuild Docker and run smoke/E2E.

## Non-Goals For First Pass

- Do not add web search as a fallback.
- Do not enable general-knowledge fallback by default.
- Do not rely only on prompt wording for safety.
- Do not remove existing citation/debug UI.
- Do not require perfect language detection before shipping no-answer safety.

## Definition Of Done

- Ask AI never returns an official answer when no grounded evidence is selected.
- Weak evidence produces partial/no-answer, not a confident answer.
- Vietnamese questions can use English source evidence when cross-lingual retrieval finds it.
- The final response clearly reports answer mode, evidence status, citations, and verification diagnostics.
- Regression tests cover no-data, weak-data, and cross-language scenarios.
