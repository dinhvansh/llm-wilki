# Ask AI NotebookLM-Inspired Upgrade Plan

## Quick Status

| Scope | Status | Verified On |
|---|---|---|
| Phase A - Source-scoped Ask and notebook context selection | Done | local regression, frontend build, Docker smoke, and E2E smoke on 2026-05-05 |
| Phase B - Query planner and decomposition | Done | local regression, planner eval subset, frontend build, Docker smoke, and E2E smoke on 2026-05-05 |
| Phase C - Notebook note layer over existing ingest artifacts | Done | local regression, notebook eval subset, retrieval benchmark, Docker smoke, and E2E smoke on 2026-05-05 |
| Phase D - Guided prompting and suggestion layer | Done | local regression, frontend build, notebook eval subset, Docker smoke, and E2E smoke on 2026-05-05 |
| Phase E - Authority-first synthesis and notebook-style answering | Done | local regression, authority-rich regressions, full eval, Docker smoke, and E2E smoke on 2026-05-05 |
| Phase F - Eval, benchmark, and operator feedback loop for notebook behavior | Done | local regression, full eval, notebook eval subset, retrieval benchmark, Docker smoke, and E2E smoke on 2026-05-05 |
| Current overall state | Phase A-F done | Ask AI now supports strict source/page/collection scope, planner-driven decomposition, notebook context retrieval, dynamic suggestion prompts, authority-first conflict reasoning, notebook-style answer sections, notebook eval metrics, and verified Docker/local end-to-end flows |

## Verification Format

- `Implementation log`: ghi lai code, endpoint, schema, va UI da them.
- `Verification`: ghi local regression, frontend build, benchmark, smoke, va eval da chay.
- `Done` chi duoc tick khi behavior da co that va da verify.
- `Suggested prompts` chi duoc xem la xong khi da co backend generation + frontend render + test behavior.

## How To Use This Plan

- File nay tiep noi plan cu, khong thay the.
- Plan cu da dong phase 1-4 cho retrieval/eval foundation.
- File nay tap trung vao buoc tiep theo: lam Ask AI thong minh hon theo huong NotebookLM, nhung van grounded-first va tan dung artifact da co.
- Khi lam xong phase nao:
  - tick checklist
  - cap nhat `Implementation log`
  - cap nhat `Verification`
  - doi `Quick Status`

## 0. Muc tieu tong the

Hien tai Ask AI da lam tot hon mot RAG co ban, nhung van chua giong tro ly doc tai lieu thuc thu.

Can dich chuyen tu:

```text
User question
-> retrieve chunks / claims / summaries
-> answer
```

sang:

```text
User question
-> xac dinh pham vi tai lieu
-> hieu y dinh va tach y neu can
-> retrieve tu lop notebook context truoc
-> tong hop theo authority / recency / scope
-> de xuat follow-up hop ly
-> tra loi theo evidence blocks ro rang
```

Muc tieu cu the:

- Ask AI phu hop hon voi usage document assistant
- giam nhieu hon cac case chat tu nhien bi troi nguon
- giup user dat cau hoi dung bang suggestion layer
- giai quyet tot hon case summary / compare / analysis / authority / conflict
- van giu grounded, citation, provenance, va debug trace

## 1. Target Product Behavior

Ask AI sau nang cap can co hanh vi sau:

### 1.1. Source-first

- User co the hoi trong:
  - 1 source
  - 1 collection
  - 1 page
  - hoac toan knowledge base
- Neu user dang dung source/page context thi Ask AI phai uu tien pham vi do.
- Neu user hoi mo ho va chua co scope, UI nen goi y chon source/collection truoc.

### 1.2. Notebook context over raw chunks

- Moi source can co lop note layer:
  - source brief
  - key points
  - procedures
  - rules / thresholds
  - risks / caveats
  - decisions
  - glossary terms
- Retrieval uu tien lop nay truoc raw chunk.

### 1.3. Query planning

- Nhieu cau hoi dai can duoc phan ra thanh sub-questions.
- Follow-up mo ho can bi hoi lai hoac duoc rewrite co cau truc.
- He thong phai biet khi nao can:
  - summary
  - compare
  - authority resolution
  - procedure extraction
  - risk review

### 1.4. Guided prompting

- UI phai goi y:
  - cau hoi bat dau
  - follow-up hop ly
  - authority/conflict prompts
  - source-specific prompts
- Suggestion layer phai la dynamic, khong phai list tinh.

### 1.5. Synthesis and reasoning

- Khi nhieu nguon cung duoc lay, Ask AI phai noi ro:
  - nguon nao official hon
  - nguon nao moi hon
  - nguon nao dang effective
  - co conflict hay khong
- Cau tra loi can giong notebook assistant hon:
  - direct answer
  - why
  - evidence by source
  - conflicts / caveats
  - recommended next question

---

## 2. Execution Plan

Thu tu thuc thi de xuat:

```text
A. Source-scoped Ask
B. Query planner
C. Notebook note layer
D. Guided prompting and suggestions
E. Authority-first synthesis
F. Eval and operator feedback loop
```

### Phase A: Source-Scoped Ask And Notebook Context Selection

Muc tieu:
- bien pham vi hoi dap thanh first-class input
- giam retrieval drift khi user dang lam viec tren 1 tai lieu hoac 1 collection ro rang

Checklist:
- [x] Them `ask scope` vao contract backend
- [x] Ho tro scope theo `sourceId`
- [x] Ho tro scope theo `collectionId`
- [x] Ho tro scope theo `pageId`
- [x] Ho tro `scope summary` trong response de UI hien user dang hoi tren pham vi nao
- [x] Them retrieval filter uu tien object trong scope truoc object ngoai scope
- [x] Them fallback policy neu scope qua hep va khong du evidence
- [x] Them UI chon scope trong Ask page
- [x] Them quick action `Ask about this source` tu Source Detail / Page Detail / Collection view
- [x] Them regression test cho scoped ask

Acceptance criteria:
- user hoi trong source cu the thi Ask AI khong troi sang source khac neu khong can
- diagnostics cho thay scope da duoc ap dung
- neu scope qua hep va khong co evidence, response noi ro da het evidence trong scope thay vi retrieve bua toan KB

Implementation log:
- 2026-05-05: Extended `AskRequest` / `AskResponseOut` in `backend/app/schemas/query.py` with `sourceId` request support and `scope` response metadata.
- 2026-05-05: Updated `backend/app/api/query.py` and `backend/app/services/query.py` so `ask()` now accepts `source_id`, resolves strict scope summaries, and filters retrieval candidates by `source`, `page`, and `collection`.
- 2026-05-05: Added strict scope exhaustion handling in `backend/app/services/query.py` so weak in-scope vector matches no longer masquerade as grounded evidence when lexical support is missing.
- 2026-05-05: Updated Ask UI in `llm-wiki/src/app/(main)/ask/page.tsx` to show current scope, keep scope with session state, support collection selection, and restore scoped sessions correctly.
- 2026-05-05: Added scoped entry points:
  - `Ask This Source` in `llm-wiki/src/app/(main)/sources/[id]/page.tsx`
  - `Ask This Page` in `llm-wiki/src/app/(main)/pages/[slug]/page.tsx`
  - `Ask this collection` in `llm-wiki/src/app/(main)/collections/page.tsx`
- 2026-05-05: Added `backend/scripts/test_phase48.py` and wired it into `scripts/run_regression.ps1` and `scripts/run_document_qa_suite.ps1`.

Verification:
- Local: `python backend\scripts\test_phase48.py` PASS.
- Local: `python backend\scripts\test_phase33.py` PASS.
- Local: `powershell -ExecutionPolicy Bypass -File .\scripts\run_regression.ps1 -SkipDocker -SkipE2E` PASS.
- Local: `python -m compileall backend\app backend\scripts` PASS.
- Frontend: `npm --prefix llm-wiki run build` PASS.
- Docker: `docker compose up -d --build postgres redis drawio backend worker frontend` PASS.
- Docker: `powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1 -SkipBuild` PASS.
- E2E: `powershell -ExecutionPolicy Bypass -File .\scripts\e2e_smoke.ps1` PASS.

### Phase B: Query Planner And Decomposition

Muc tieu:
- nang Ask AI tu intent detection don gian thanh planner cho document reasoning
- xu ly tot hon cau dai, nhieu ve, va follow-up hoi thoai

Checklist:
- [x] Them `query planner` object trong backend
- [x] Phan loai question thanh:
  - summary
  - definition
  - procedure
  - compare
  - authority_check
  - conflict_check
  - risk_review
  - change_review
- [x] Them decomposition cho cau nhieu y
- [x] Them `ask back` template co cau truc cho follow-up mo ho
- [x] Them `planning diagnostics` vao response/admin debug
- [x] Them retrieval policy selection dua tren planner result
- [x] Them regression tests cho multi-part analysis questions

Acceptance criteria:
- cau hoi kieu `can chuan bi gi, rui ro gi, test gi truoc` duoc tach thanh sub-questions hop ly
- follow-up kieu `cai tren`, `cai do`, `luu y nua khong` duoc noi vao context truoc hoac bi hoi lai ro rang
- planner result hien duoc trong diagnostics va admin view

Implementation log:
- 2026-05-05: Extended `backend/app/services/query.py` with a planner layer that now emits `single_query`, `followup_rewrite`, `ask_back`, or `decompose` strategies before retrieval.
- 2026-05-05: Added multi-part clause decomposition for long analysis questions, plus planner-safe follow-up rewrite handling so conversational rewrites do not get misclassified as analysis.
- 2026-05-05: Refactored retrieval into per-subquery execution and merge flow, preserving existing chunk/claim/section-summary/knowledge-unit retrieval while letting planner steps contribute separately.
- 2026-05-05: Added planning-aware rerank and context assembly so procedure and risk sub-questions can surface different evidence roles inside one answer.
- 2026-05-05: Extended response payloads and Ask UI diagnostics to show planner strategy and sub-queries in admin/debug surfaces.
- 2026-05-05: Added `backend/scripts/test_phase50.py`, planner eval coverage in `backend/evals/golden_dataset.json`, and extended `backend/scripts/evaluate_quality.py`.

Verification:
- Local: `python backend\scripts\test_phase50.py` PASS.
- Local: `python backend\scripts\test_phase49.py` PASS.
- Eval: `python backend\scripts\evaluate_quality.py --tag planner` PASS.
- Eval: `python backend\scripts\evaluate_quality.py` PASS.
- Local: `powershell -ExecutionPolicy Bypass -File .\scripts\run_regression.ps1 -SkipDocker -SkipE2E` PASS.
- Local: `python -m compileall backend\app backend\scripts` PASS.
- Frontend: `npm --prefix llm-wiki run build` PASS.
- Docker: `docker compose up -d --build postgres redis drawio backend worker frontend` PASS.
- Docker: `powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1 -SkipBuild` PASS.
- E2E: `powershell -ExecutionPolicy Bypass -File .\scripts\e2e_smoke.ps1` PASS after one rerun due post-recreate timing race.

### Phase C: Notebook Note Layer Over Existing Ingest Artifacts

Muc tieu:
- tan dung `section summaries`, `claims`, `knowledge_units`, `page summaries`
- dong goi thanh lop notebook context de retrieval doc duoc tai lieu theo y nghia, khong chi theo chunk

Checklist:
- [x] Din h nghia `note layer` object model dua tren artifact hien co
- [x] Them `source brief` generation trong ingest
- [x] Them `key points` generation cho moi source
- [x] Them `procedures`, `rules`, `risks`, `decisions` grouping tu `knowledge_units + claims`
- [x] Them persisted `notebook context` vao source metadata hoac object moi
- [x] Uu tien retrieve tu `source brief / key points / grouped notes` truoc raw chunks
- [x] Them provenance mapping tu note layer ve source/chunk/claim goc
- [x] Them UI doc notebook summary tren Source Detail
- [x] Them regression tests cho note-layer retrieval

Acceptance criteria:
- source co mot lop context ngan gon de Ask AI dua vao truoc khi xuong raw text
- note layer van truy vet duoc ve evidence goc
- top candidates cho summary/procedure/analysis giam nhieu nhieu source nhieu chunk vo nghia

Implementation log:
- 2026-05-05: Added notebook context generation in `backend/app/services/sources.py`, including `sourceBrief`, `keyPoints`, grouped notebook notes, provenance, and recommended prompts persisted into `source.metadata_json["notebookContext"]`.
- 2026-05-05: Extended `backend/app/services/query.py` so retrieval and citations support `notebook_note` candidates alongside `section_summary`, `claim`, `knowledge_unit`, and `chunk`.
- 2026-05-05: Updated Source Detail to surface notebook context and `Ask next` CTAs from notebook prompts.
- 2026-05-05: Added `backend/scripts/test_phase51.py` and benchmark notebook-context signal coverage in `backend/scripts/benchmark_retrieval.py`.

Verification:
- Local: `python backend\scripts\test_phase51.py` PASS.
- Benchmark: `python backend\scripts\benchmark_retrieval.py` PASS.
- Local: `powershell -ExecutionPolicy Bypass -File .\scripts\run_regression.ps1 -SkipDocker -SkipE2E` PASS.
- Docker/E2E: `docker_smoke.ps1` PASS, `e2e_smoke.ps1` PASS.

### Phase D: Guided Prompting And Suggestion Layer

Muc tieu:
- giup user hoi dung kieu he thong manh
- huong hoi thoai di theo duong ray thay vi de user tu do gay retrieval drift

Checklist:
- [x] Them `suggestedPrompts` vao Ask response
- [x] Them prompt suggestions khi chua bat dau chat
- [x] Them follow-up suggestions sau moi answer
- [x] Sinh suggestion dua tren:
  - scope hien tai
  - document type
  - interpreted intent
  - selected evidence
  - conflict / uncertainty state
- [x] Them suggestion templates cho:
  - summary
  - procedure
  - compare
  - authority
  - conflict
  - change review
- [x] Them UI chips cho suggestion layer
- [x] Them CTA `Ask next` trong Source Detail / Page Detail
- [x] Them regression tests cho suggestion generation

Acceptance criteria:
- user co prompt chips huu ich truoc va sau khi hoi
- suggestions khong phai list tinh, ma doi theo source/type/intent
- suggestions dan user vao cau hoi grounded hon thay vi chat mo ho

Implementation log:
- 2026-05-05: Extended `AskResponse` contract with `suggestedPrompts` in `backend/app/schemas/query.py` and `llm-wiki/src/lib/types/index.ts`.
- 2026-05-05: Added dynamic suggestion generation in `backend/app/services/query.py`, driven by scope, inferred document type, intent, uncertainty, selected evidence, and conflict state.
- 2026-05-05: Updated mock/real query services and ask hooks so suggestion payloads flow end-to-end through the current Ask UI stack.
- 2026-05-05: Updated `llm-wiki/src/app/(main)/ask/page.tsx` to render:
  - scope-aware starter prompts before chat
  - suggested follow-up chips after each answer
  - click-to-ask behavior for guided follow-ups
- 2026-05-05: Added `backend/scripts/test_phase49.py` and wired it into `scripts/run_regression.ps1` and `scripts/run_document_qa_suite.ps1`.

Verification:
- Local: `python backend\scripts\test_phase49.py` PASS.
- Frontend: `npm --prefix llm-wiki run build` PASS.
- Local: `powershell -ExecutionPolicy Bypass -File .\scripts\run_regression.ps1 -SkipDocker -SkipE2E` PASS.
- Docker: `powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1 -SkipBuild` PASS.
- E2E: `powershell -ExecutionPolicy Bypass -File .\scripts\e2e_smoke.ps1` PASS.

### Phase E: Authority-First Synthesis And Notebook-Style Answering

Muc tieu:
- cho Ask AI tra loi thong minh hon nhung van grounded-first
- tong hop nguon theo authority, recency, effective date, va approval state

Checklist:
- [x] Nâng synthesis policy cho `official > reference > informal`
- [x] Them uu tien `approved > draft > archived`
- [x] Them `effective_date` va `version` vao conflict reasoning
- [x] Them answer sections:
  - direct answer
  - why
  - evidence by source
  - conflicts / caveats
  - uncertainty
  - recommended next question
- [x] Them authority explanation trong answer khi co nhieu nguon
- [x] Them `recommended next prompts` dua tren answer state
- [x] Them regression tests cho authority-rich compare/conflict scenarios

Acceptance criteria:
- so sanh 2 nguon cho thay nguon nao nen uu tien va vi sao
- conflict answer khong chi neu xung dot, ma neu ca cach ket luan tam thoi
- answer schema giong mot notebook assistant hon mot doan text ngau nhien

Implementation log:
- 2026-05-05: Extended conflict reasoning with `effectiveDate`, `version`, authority level, and approval state in `backend/app/services/query.py`.
- 2026-05-05: Upgraded default answer formatting to notebook-style sections: `Direct Answer`, `Why`, `Evidence By Source`, `Conflicts / Caveats`, `Uncertainty / Missing Evidence`, and `Recommended Next Question`.
- 2026-05-05: Tightened explicit-source retrieval for named conflict/authority questions so unrelated sources are filtered out before ranking.
- 2026-05-05: Added `backend/scripts/test_phase52.py` for authority-rich notebook answer-schema regression.

Verification:
- Local: `python backend\scripts\test_phase52.py` PASS.
- Eval: `python backend\scripts\evaluate_quality.py --tag notebook` PASS.
- Full eval: `python backend\scripts\evaluate_quality.py` PASS.

### Phase F: Eval, Benchmark, And Operator Feedback Loop For Notebook Behavior

Muc tieu:
- do duoc xem nang cap notebook-inspired co tot len that hay khong
- bao dam co feedback loop cho operator va developer

Checklist:
- [x] Them eval subset cho:
  - scoped ask
  - multi-part analysis
  - suggestion usefulness
  - notebook-style summary
  - authority-first synthesis
- [x] Them benchmark truoc/sau cho note-layer retrieval
- [x] Them metrics moi:
  - scope adherence
  - decomposition success
  - follow-up recovery
  - suggestion click/usefulness proxy
- [x] Them admin debug surface cho planner + suggestion + scope trace
- [x] Them quality release gate cho notebook behaviors
- [x] Cap nhat automated suite de chay notebook scenarios

Acceptance criteria:
- co so lieu de biet Ask AI thong minh hon o nhung case nao
- operator debug duoc planner path, scope path, suggestion path, va authority reasoning
- quality gate chan regression khi doi retrieval/planner/suggestion

Implementation log:
- 2026-05-05: Extended `backend/evals/golden_dataset.json` and `backend/scripts/evaluate_quality.py` with notebook behavior cases for scoped ask, notebook summary, authority synthesis, and suggestion usefulness.
- 2026-05-05: Added notebook behavior metrics and quality gates: `scopeAdherence`, `notebookSummaryAccuracy`, `authoritySynthesisAccuracy`, and `suggestionUsefulnessProxy`.
- 2026-05-05: Extended `backend/scripts/benchmark_retrieval.py` with notebook-context benchmark coverage and updated automation scripts to include `test_phase51.py`, `test_phase52.py`, and notebook-tag eval runs.
- 2026-05-05: Verified admin quality surface still renders the new metrics and behavior cases from the persisted reports.

Verification:
- Local: `python backend\scripts\evaluate_quality.py` PASS.
- Local: `python backend\scripts\evaluate_quality.py --tag notebook` PASS.
- Local: `python backend\scripts\benchmark_retrieval.py` PASS.
- Local: `powershell -ExecutionPolicy Bypass -File .\scripts\run_regression.ps1 -SkipDocker -SkipE2E` PASS.
- Docker/E2E: `powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1 -SkipBuild` PASS, `powershell -ExecutionPolicy Bypass -File .\scripts\e2e_smoke.ps1` PASS.

---

## 3. Detailed Design Map

### 3.1. Backend Areas Likely Touched

- `backend/app/services/query.py`
- `backend/app/schemas/query.py`
- `backend/app/api/query.py`
- `backend/app/core/ingest.py`
- `backend/app/services/sources.py`
- `backend/app/models/records.py`
- `backend/app/services/quality_runs.py`
- `backend/scripts/evaluate_quality.py`
- `backend/scripts/benchmark_retrieval.py`

### 3.2. Frontend Areas Likely Touched

- `llm-wiki/src/app/(main)/ask/page.tsx`
- `llm-wiki/src/lib/types/index.ts`
- `llm-wiki/src/hooks/use-ask.ts`
- `llm-wiki/src/services/real-query.ts`
- source/page/collection entry points them `Ask in scope`

### 3.3. Workstream Mapping

- Phase A -> scope contract, scope-aware retrieval, scope UI
- Phase B -> query planner, decomposition, ask-back
- Phase C -> notebook note layer and source brief
- Phase D -> dynamic suggestion generation and prompt chips
- Phase E -> authority-first synthesis and richer answer schema
- Phase F -> eval, benchmark, admin drilldown, release gate

---

## 4. Suggested Commit Order

1. Scope contract and backend filtering
2. Ask UI scope selector and entry CTAs
3. Query planner and decomposition
4. Source brief and note-layer generation
5. Note-layer retrieval priority
6. Suggested prompts backend contract
7. Prompt chips UI
8. Authority-first synthesis refinement
9. Eval and benchmark extensions
10. Admin notebook-debug surface

---

## 5. Phase Done Checklist

### Phase A Done Checklist

- [x] Scope request/response contract merged
- [x] Scope-aware retrieval verified
- [x] Ask UI supports scope
- [x] Source/Page/Collection entry points support scoped ask
- [x] Regression and E2E pass

### Phase B Done Checklist

- [x] Query planner active
- [x] Decomposition active
- [x] Ambiguous follow-up ask-back improved
- [x] Diagnostics exposed
- [x] Eval subset pass

### Phase C Done Checklist

- [x] Source brief generated
- [x] Grouped notebook notes generated
- [x] Provenance mapping preserved
- [x] Retrieval prefers notebook layer first
- [x] Benchmark improved

### Phase D Done Checklist

- [x] Suggested prompts generated dynamically
- [x] Prompt chips rendered in UI
- [x] Follow-up suggestions grounded to evidence
- [x] Suggestion regression pass

### Phase E Done Checklist

- [x] Authority-first synthesis enabled
- [x] Notebook-style answer schema enabled
- [x] Recommended next question generated
- [x] Authority/conflict eval pass

### Phase F Done Checklist

- [x] Notebook eval subset added
- [x] Metrics recorded
- [x] Admin trace updated
- [x] Automated suite updated
- [x] Release gate updated

---

## 6. Open Questions And Guardrails

- Khong bien Ask AI thanh chatbot freestyle. Van uu tien grounded-first.
- Khong de suggestion layer tro thanh prompt spam. Moi lan chi nen de vai prompt co gia tri.
- Khong de note layer cat dut provenance. Moi notebook note phai truy duoc ve source/chunk/claim goc.
- Neu scope va evidence mau thuan, phai uu tien minh bach ve uncertainty hon la tra loi tu tin.
- Neu planner khong chac, nen hoi lai user thay vi decomposition bua.

---

## 7. Recommended Starting Point

Neu bat dau implement ngay, thu tu toi uu cho repo hien tai la:

1. Phase A
2. Phase D phan prompt chips co ban
3. Phase B
4. Phase C
5. Phase E
6. Phase F

Ly do:

- Phase A giam drift nhanh nhat.
- Suggestion layer som se day user vao duong hoi dung.
- Planner va note layer sau do moi nang chat luong tra loi len ro rang.
