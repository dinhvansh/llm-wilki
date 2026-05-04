# Full Plan — Nâng cấp AI Document Processing & Ask AI Accuracy cho LLM Wiki

## Quick Status

| Scope | Status | Verified On |
|---|---|---|
| Phase 1 - Ask AI retrieval and answer quality | Done | local regression, benchmark, Docker smoke, E2E smoke on 2026-05-04 |
| Phase 2 - Ingest metadata and semantic structure | Planned | Not started |
| Phase 3 - Knowledge units and retrieval objects | Planned | Not started |
| Phase 4 - Eval, benchmark, and quality gates | Planned | Not started |
| Current overall state | Planning | This file is implementation backlog and checklist |

## Verification Format

- `Implementation log`: ghi lai code, behavior, migration, va endpoint da them.
- `Verification`: ghi cach xac nhan phase sau khi lam xong.
- `Done` chi duoc tick khi da co it nhat local regression va build pass.
- `Verified` chi duoc ghi khi da co local regression + frontend build + smoke/regression lien quan.

## How To Use This Plan

- Phan tren cung la execution plan theo format cu: phase, checklist, acceptance criteria, verification.
- Phan ben duoi giu detailed design, prompt, schema, va target architecture.
- Khi bat dau implement phase nao, tick checklist trong phase do.
- Khi xong phase, them `Implementation log` va `Verification` ngay ben duoi phase.

## 0. Mục tiêu tổng thể

Hiện tại hệ thống đã có nền tảng:

```text
Upload source
→ parse
→ chunk
→ claim extraction
→ page generation
→ glossary / entity / timeline / review queue / graph
→ Ask AI
```

Nhưng điểm yếu chính là:

```text
chunk còn hơi thô
retrieval còn đơn giản
Ask AI chưa hiểu tốt follow-up
answer chưa đủ guardrail
chưa có eval để đo tốt/xấu
```

Mục tiêu nâng cấp:

```text
Tài liệu gốc
→ hiểu cấu trúc tài liệu
→ chunk theo semantic unit
→ enrich metadata
→ retrieve đa tầng
→ rerank
→ assemble context thông minh
→ answer có citation/provenance rõ
→ đo chất lượng bằng eval set
```

---

## 1. Target Architecture

### 1.1. Kiến trúc pipeline mới

```text
[Source Upload / Manual Note]
        ↓
[Document Type Classification]
        ↓
[Structure-aware Parsing]
        ↓
[Semantic Chunking]
        ↓
[Metadata Enrichment]
        ↓
[Knowledge Extraction]
        ↓
[Parent Chunk / Section Summary]
        ↓
[Indexing]
        ↓
[Multi-source Retrieval]
        ↓
[Re-ranking]
        ↓
[Context Assembly]
        ↓
[Grounded Answer Generation]
        ↓
[Quality Check / Citation Check]
        ↓
[Answer + Evidence + Uncertainty]
```

### 1.2. Các object chính

Hệ thống không nên chỉ retrieve từ `source_chunks`.

Nên có các object sau:

```text
sources
source_sections
source_chunks
section_summaries
claims
knowledge_units
pages
page_summaries
entities
glossary_terms
timeline_events
issues
citations
```

Ask AI nên retrieve từ nhiều nguồn:

```text
chunks + claims + section summaries + page summaries + knowledge units + glossary terms + entities
```

---

## 1.3. Execution Plan

Thu tu thuc thi de xuat cho repo hien tai:

```text
1. Fix Ask AI truoc
2. Nang ingest de retrieval tot hon
3. Chuan hoa retrieval objects va knowledge units
4. Them eval, benchmark, va quality gates
```

### Phase 1: Fix Ask AI First

Muc tieu:
- giam loi follow-up, retrieve sai chunk, va tra loi lech y
- dua `Ask AI` tu single-turn retrieval thanh chat-aware grounded QA
- them scoring/rerank va schema tra loi ro rang

Checklist:
- [x] Them conversational query rewrite
- [x] Them intent detection va ambiguous follow-up handling
- [x] Them chat-history-aware retrieval context
- [x] Retrieve tu `source_chunks + claims + page summaries`
- [x] Them source priority / authority ranking vao retrieval score
- [x] Them rerank top candidates
- [x] Them context assembly theo coverage
- [x] Them answer schema: `direct answer / evidence / uncertainty`
- [x] Them conflict-aware answer handling
- [x] Them retrieval debug log cho admin
- [x] Them regression test cho follow-up, ambiguity, va conflict

Acceptance criteria:
- follow-up kieu `cai do`, `y toi la`, `tra loi sai roi` khong con retrieve bua khi context khong du
- `Ask AI` uu tien dung source approved / moi hon / authority cao hon khi evidence xung dot
- response tach ro `direct answer`, `evidence`, `uncertainty`
- admin xem duoc standalone query, top candidates, rerank ly do, va selected context

Implementation log:
- 2026-05-04: Extended `Ask AI` contract in `backend/app/schemas/query.py` and `backend/app/api/query.py` to return `interpretedQuery`, `answerType`, `uncertainty`, `conflicts`, `retrievalDebugId`, and richer diagnostics.
- 2026-05-04: Refactored `backend/app/services/query.py` to add follow-up-aware query understanding, clarification handling for ambiguous follow-ups, candidate retrieval from `chunks + claims + page summaries`, initial authority/freshness/approval scoring, and structured answer sections.
- 2026-05-04: Updated frontend ask types/UI in `llm-wiki/src/lib/types/index.ts` and `llm-wiki/src/app/(main)/ask/page.tsx` to show interpreted query, uncertainty, conflict summary, and admin candidate diagnostics.
- 2026-05-04: Added `backend/scripts/test_phase33.py` and wired it into `scripts/run_regression.ps1`.
- 2026-05-04: Added rerank pass, context coverage diagnostics, conflict scoring improvements, and benchmark before/after comparison in `backend/scripts/benchmark_retrieval.py`.

Verification:
- Local: `python backend\scripts\test_phase33.py` PASS.
- Local: `python backend\scripts\test_ask_history.py` PASS.
- Local: `python backend\scripts\benchmark_retrieval.py` PASS.
- Local: `python -m compileall backend\app backend\scripts` PASS.
- Frontend: `npm --prefix llm-wiki run build` PASS.
- Docker: `docker compose up -d --build postgres redis drawio backend worker frontend` PASS.
- Docker: `powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1 -SkipBuild` PASS.
- E2E: `powershell -ExecutionPolicy Bypass -File .\scripts\e2e_smoke.ps1` PASS.

### Phase 2: Upgrade Ingest And Metadata

Muc tieu:
- tang chat luong semantic structure truoc khi index
- giup retrieval khop dung document role thay vi chi match tu khoa

Checklist:
- [ ] Them document-type classification theo content purpose
- [ ] Them section-role detection
- [ ] Them semantic-unit chunking rules theo `sop / policy / report / glossary`
- [ ] Them parent chunk / section summary
- [ ] Enrich metadata cho chunk va section
- [ ] Bo sung source metadata: `source_status`, `source_type`, `authority_level`, `effective_date`, `version`, `owner`
- [ ] Cho phep manual override document type / authority neu classifier khong chac
- [ ] Them regression test cho parser/chunker metadata moi

Acceptance criteria:
- chunk moi co du metadata toi thieu de retrieval filter va rerank
- tai lieu SOP / policy / report khong bi cat ngang y chinh o cac phan quan trong
- source metadata du de giai quyet conflict `old vs new`, `draft vs approved`, `policy vs note`

Implementation log:
- Pending

Verification:
- Pending

### Phase 3: Retrieval Objects And Knowledge Units

Muc tieu:
- mo rong retrieval surface beyond raw chunks
- dua tri thuc co cau truc vao Ask AI va page generation

Checklist:
- [ ] Them / chuan hoa `source_sections`
- [ ] Them / chuan hoa `section_summaries`
- [ ] Them / chuan hoa `page_summaries`
- [ ] Chuan hoa `knowledge_units`
- [ ] Index retrieval cho `claims`, `section summaries`, `page summaries`, `knowledge_units`
- [ ] Them retrieval policy theo intent: definition / procedure / policy / comparison / conflict
- [ ] Them citation/provenance link day du tu retrieval object ve source evidence
- [ ] Them regression test cho multi-object retrieval

Acceptance criteria:
- query dinh nghia uu tien glossary / definition units khi phu hop
- query quy trinh uu tien procedure steps + section summary
- query policy/conflict co the trich duoc rule + exception + authority context

Implementation log:
- Pending

Verification:
- Pending

### Phase 4: Eval, Benchmark, And Quality Gates

Muc tieu:
- do duoc retrieval va answer quality thay vi sua theo cam giac
- khoa chat regression khi thay doi prompt/retrieval

Checklist:
- [ ] Tao fixed eval set
- [ ] Them eval runner
- [ ] Them benchmark command cho retrieval/answer quality
- [ ] Them metrics: recall, precision, faithfulness, unsupported claim rate
- [ ] Them quality gate cho conflict handling va clarification accuracy
- [ ] Them lint / check cho unsupported claims, stale source, authority mismatch
- [ ] Them admin/debug surface de doc ket qua eval

Acceptance criteria:
- moi thay doi retrieval quan trong deu co benchmark truoc/sau
- co bo case cover follow-up, ambiguity, conflict, insufficient evidence, source lookup
- co baseline metrics de so sanh qua cac sprint

Implementation log:
- Pending

Verification:
- Pending

---

## 1.4. Detailed Design Map

Bang nay dung de map phan execution plan o tren voi cac muc detailed design o ben duoi.

### Phase 1 maps to

- `Them conversational query rewrite`
  Design refs: `2.1. Conversational Query Rewrite`, `10.1. Query Rewrite Prompt`, `8.2. Query rewrite endpoint`
- `Them intent detection va ambiguous follow-up handling`
  Design refs: `2.1. Conversational Query Rewrite`, `9. Step 2 - Query Understanding`
- `Them chat-history-aware retrieval context`
  Design refs: `2.2. Chat History Aware Retrieval`, `8.1. Ask AI endpoint`, `9. Step 1 - Receive user query`
- `Retrieve tu source_chunks + claims + page summaries`
  Design refs: `2.3. Multi-source Candidate Retrieval`, `9. Step 3 - Retrieve Candidates`
- `Them source priority / authority ranking vao retrieval score`
  Design refs: `5. Phase 4 - Source Priority / Authority Ranking`, `2.5. Scoring de xuat`
- `Them rerank top candidates`
  Design refs: `2.4. Candidate Retrieval Strategy`, `2.6. Reranking`, `10.2. Reranker Prompt`
- `Them context assembly theo coverage`
  Design refs: `2.7. Context Assembly theo coverage`, `9. Step 5 - Context Assembly`, `10.3. Context Assembly Prompt`
- `Them answer schema: direct answer / evidence / uncertainty`
  Design refs: `2.8. Answer Generation Schema`, `9. Step 6 - Generate Answer`, `10.4. Answer Generation Prompt`
- `Them conflict-aware answer handling`
  Design refs: `2.8. Answer Generation Schema`, `5. Phase 4 - Source Priority / Authority Ranking`, `14.4. Conflict giua source`
- `Them retrieval debug log cho admin`
  Design refs: `7.8. retrieval_logs`, `14.1. Query rewrite sai`, `14.2. Reranker chon sai`
- `Them regression test cho follow-up, ambiguity, va conflict`
  Design refs: `6. Phase 5 - Eval Set & Benchmark`, `15. Checklist trien khai / Quality`

### Phase 2 maps to

- `Them document-type classification theo content purpose`
  Design refs: `3.1. Document Type Classification`
- `Them section-role detection`
  Design refs: `3.2. Section Role Detection`
- `Them semantic-unit chunking rules theo sop / policy / report / glossary`
  Design refs: `3.3. Semantic Unit Chunking`
- `Them parent chunk / section summary`
  Design refs: `3.4. Parent Chunk / Section Summary`, `7.2. source_sections`
- `Enrich metadata cho chunk va section`
  Design refs: `3.5. Metadata Enrichment`, `7.3. source_chunks`
- `Bo sung source metadata: source_status, source_type, authority_level, effective_date, version, owner`
  Design refs: `5.2. Metadata can them cho source`, `7.1. sources`
- `Cho phep manual override document type / authority neu classifier khong chac`
  Design refs: `14.3. Metadata classifier sai`
- `Them regression test cho parser/chunker metadata moi`
  Design refs: `6. Phase 5 - Eval Set & Benchmark`, `15. Checklist trien khai / Ingest`

### Phase 3 maps to

- `Them / chuan hoa source_sections`
  Design refs: `7.2. source_sections`
- `Them / chuan hoa section_summaries`
  Design refs: `3.4. Parent Chunk / Section Summary`
- `Them / chuan hoa page_summaries`
  Design refs: `1.2. Cac object chinh`, `2.3. Multi-source Candidate Retrieval`
- `Chuan hoa knowledge_units`
  Design refs: `4. Phase 3 - Knowledge Units`, `7.5. knowledge_units`
- `Index retrieval cho claims, section summaries, page summaries, knowledge_units`
  Design refs: `2.3. Multi-source Candidate Retrieval`, `9. Step 3 - Retrieve Candidates`
- `Them retrieval policy theo intent: definition / procedure / policy / comparison / conflict`
  Design refs: `2.1. Intent can detect`, `2.7. Context Assembly theo coverage`, `4.3. Ask AI dung knowledge units the nao?`
- `Them citation/provenance link day du tu retrieval object ve source evidence`
  Design refs: `7.7. citations`, `9. Step 8 - Return Answer + Evidence`
- `Them regression test cho multi-object retrieval`
  Design refs: `6. Phase 5 - Eval Set & Benchmark`, `15. Checklist trien khai / Quality`

### Phase 4 maps to

- `Tao fixed eval set`
  Design refs: `6.2. Tao bo cau hoi noi bo`, `7.9. eval_cases`
- `Them eval runner`
  Design refs: `8.5. Eval endpoint`, `7.10. eval_runs`
- `Them benchmark command cho retrieval/answer quality`
  Design refs: `6.6. Benchmark command`
- `Them metrics: recall, precision, faithfulness, unsupported claim rate`
  Design refs: `6.5. Metrics`
- `Them quality gate cho conflict handling va clarification accuracy`
  Design refs: `6.4. Expected behavior`, `6.5. Metrics`
- `Them lint / check cho unsupported claims, stale source, authority mismatch`
  Design refs: `9. Step 7 - Grounding Check`, `15. Checklist trien khai / Quality`
- `Them admin/debug surface de doc ket qua eval`
  Design refs: `15. Checklist trien khai / Frontend`, `7.8. retrieval_logs`, `7.10. eval_runs`

### Completion Checklist

Khi dong phase, cap nhat theo thu tu:

1. Tick cac item da xong trong `Checklist` cua phase.
2. Ghi `Implementation log` theo moc ngay va nhung file/API/model da doi.
3. Ghi `Verification` voi local regression, build, va smoke/e2e lien quan.
4. Cap nhat `Quick Status` neu phase da `Done` hoac `Verified`.

---

## 1.5. Phase 1 Implementation Breakdown

Phan nay tach `Phase 1` thanh cac workstream co the implement truc tiep tren repo hien tai.

### Workstream 1 - Schema And Diagnostics Contract

Muc tieu:
- mo rong request/response cua `Ask AI` de support query understanding, authority-aware retrieval, va debug

Files likely touched:
- `backend/app/schemas/query.py`
- `backend/app/api/query.py`
- `llm-wiki/src/services/real-query.ts`
- `llm-wiki/src/services/types.ts`
- `llm-wiki/src/lib/types/index.ts`
- `llm-wiki/src/app/(main)/ask/page.tsx`

Checklist:
- [x] Mo rong `AskRequest` de nhan them `collectionId`, `pageId`, `chatHistory` neu can
- [x] Mo rong `AskResponseOut` de tra them `answerType`, `uncertainty`, `conflicts`, `interpretedQuery`, `retrievalDebugId`
- [x] Mo rong `AskDiagnosticsOut` de khong chi co `topChunks` ma co `topCandidates`, `selectedContext`, `clarificationTriggered`
- [x] Dam bao frontend types va services doc duoc schema moi

Acceptance criteria:
- backend va frontend thong nhat hop dong API moi cho `Ask AI`
- admin co du field de debug rewrite, retrieval, rerank, va context assembly

### Workstream 2 - Query Rewrite And Follow-up Resolution

Muc tieu:
- bien query moi hoac follow-up thanh standalone query retrieve duoc

Files likely touched:
- `backend/app/services/query.py`
- `backend/app/core/llm_client.py`
- `backend/app/core/runtime_config.py`

Checklist:
- [x] Them helper lay 3-5 luot chat gan nhat tu `ChatSession`
- [x] Them query understanding module: `standalone_query`, `intent`, `answer_type`, `target_entities`, `filters`
- [x] Them rule-based fallback khi LLM rewrite khong available
- [x] Neu ambiguous ma chat history khong du thi tra ve clarification thay vi retrieve bua
- [x] Ghi log rewrite vao diagnostics

Acceptance criteria:
- follow-up ngan van duoc resolve ve query day du khi context du
- query mo ho khong bi dua thang vao retrieval neu khong resolve duoc

### Workstream 3 - Candidate Retrieval Expansion

Muc tieu:
- mo rong retrieval tu raw chunks sang object retrieval thuc dung hon

Files likely touched:
- `backend/app/services/query.py`
- `backend/app/models/records.py`
- `backend/app/services/pages.py` hoac service lien quan den summary/page link neu can

Checklist:
- [x] Tach retrieval thanh hai tang: recall rong va rerank hep
- [x] Lay candidates tu `source_chunks`
- [x] Lay candidates tu `claims`
- [x] Lay candidates tu `page summaries`
- [x] Chuan hoa candidate shape chung: `candidate_id`, `candidate_type`, `source_id`, `page_id`, `text`, `diagnostics`
- [x] Bo sung metadata boost theo page/source relation va current scope

Acceptance criteria:
- retrieval candidate list co nhieu object type, khong chi `topChunks`
- query procedural/policy/definition co candidate phu hop hon so voi raw chunk only

### Workstream 4 - Authority-Aware Scoring And Rerank

Muc tieu:
- uu tien dung nguon official, approved, moi hon khi evidence xung dot hoac gan nhau

Files likely touched:
- `backend/app/services/query.py`
- `backend/app/models/records.py`
- `backend/app/schemas/source.py` hoac schema source lien quan
- migration moi neu can them metadata source

Checklist:
- [x] Dinh nghia authority metadata toi thieu cho source hien tai
- [x] Them scoring component: `authority_score`
- [x] Them scoring component: `freshness_score`
- [x] Them scoring component: `approval_score` hoac map tu `source_status`
- [x] Them rerank pass tren top candidates
- [x] Trong conflict, diagnostics phai chi ro tai sao source nao duoc uu tien hon

Acceptance criteria:
- retrieval score khong chi dua vao relevance
- answer co the giai thich uu tien source A hon source B khi conflict

### Workstream 5 - Context Assembly And Answer Schema

Muc tieu:
- khong nhat top-N passage mot cach co hoc; thay vao do build context theo intent va coverage

Files likely touched:
- `backend/app/services/query.py`
- `backend/app/schemas/query.py`

Checklist:
- [x] Them context assembler theo `intent`
- [x] Deduplicate candidates giong nhau
- [x] Chon context theo vai tro: definition / step / rule / exception / threshold / comparison-side
- [x] Refactor answer generation de tra ve `direct answer`, `evidence`, `uncertainty`
- [x] Neu co conflict thi tra ve `conflicts`
- [x] Neu khong du evidence thi tra ve `uncertainty` ro rang

Acceptance criteria:
- answer format on dinh va doc duoc
- context pack khong lap vo nghia
- conflict va insufficient evidence duoc the hien ro

### Workstream 6 - Admin Debug UI

Muc tieu:
- cho admin nhin thay he thong da hieu query va chon evidence ra sao

Files likely touched:
- `llm-wiki/src/app/(main)/ask/page.tsx`
- `llm-wiki/src/hooks/use-ask.ts`
- `llm-wiki/src/lib/types/index.ts`

Checklist:
- [x] Hien `interpreted query` khi user la admin
- [x] Hien `top candidates` va score diagnostics khi user la admin
- [x] Hien clarification state neu query bi coi la ambiguous
- [x] Hien context coverage va conflict diagnostics neu co

Acceptance criteria:
- admin debug duoc ly do tai sao answer dung/sai ma khong can doc DB truc tiep

### Workstream 7 - Regression And Benchmark Seed

Muc tieu:
- khoa chat regression ngay trong Phase 1 truoc khi sang eval phase day du

Files likely touched:
- `backend/scripts/test_phase*.py` moi
- `backend/scripts/benchmark_retrieval.py`
- `scripts/run_regression.ps1`

Checklist:
- [x] Them test follow-up rewrite
- [x] Them test ambiguous query -> ask clarification
- [x] Them test authority ranking conflict
- [x] Them test multi-source retrieval cho `chunks + claims + page summaries`
- [x] Them benchmark truoc/sau cho retrieval quality
- [x] Hook vao `run_regression.ps1`

Acceptance criteria:
- co regression test cho cac loi user thay ngay trong Ask AI
- phase 1 co baseline benchmark truoc khi mo rong Phase 2-4

### Suggested Commit Order

```text
1. Schema + frontend types contract
2. Query rewrite + chat history resolution
3. Candidate retrieval expansion
4. Authority-aware scoring + rerank
5. Context assembly + answer schema
6. Admin debug UI
7. Regression + benchmark seed
```

### Phase 1 Done Checklist

- [x] API request/response moi da thong
- [x] Follow-up query khong con xu ly nhu query doc lap
- [x] Retrieval da lay tu nhieu object type
- [x] Authority ranking da anh huong den candidate score
- [x] Answer co `direct answer / evidence / uncertainty`
- [x] Admin debug xem duoc interpreted query va candidate diagnostics
- [x] Regression local pass
- [x] Frontend build pass
- [x] Docker smoke/regression lien quan pass

---

## 1.6. Phase 2 Implementation Breakdown

Phan nay tach `Phase 2` thanh cac workstream de nang ingest va metadata theo dung nhu cau retrieval.

### Workstream 1 - Source Metadata Foundation

Muc tieu:
- bo sung metadata nguon de phuc vu authority ranking, recency, va scope filtering

Files likely touched:
- `backend/app/models/records.py`
- `backend/app/schemas/source.py`
- `backend/app/services/sources.py`
- `backend/app/api/sources.py`
- Alembic migration moi
- `llm-wiki/src/app/(main)/sources/*`

Checklist:
- [ ] Them metadata source: `source_status`
- [ ] Them metadata source: `authority_level`
- [ ] Them metadata source: `effective_date`
- [ ] Them metadata source: `version`
- [ ] Them metadata source: `owner`
- [ ] Them serialize/deserialize cho source metadata moi
- [ ] Hien va sua metadata nay trong Source Detail neu user co quyen

Acceptance criteria:
- moi source co du metadata toi thieu de Phase 1 authority-aware retrieval dung duoc
- admin/editor sua duoc metadata authority neu ingest khong suy ra chac chan

### Workstream 2 - Document Type Classification

Muc tieu:
- classify tai lieu theo content purpose thay vi file extension

Files likely touched:
- `backend/app/core/ingest.py`
- `backend/app/services/sources.py`
- `backend/app/models/records.py`
- script regression moi

Checklist:
- [ ] Them classifier cho `document_type`
- [ ] Ho tro cac type: `sop`, `policy`, `report`, `proposal`, `meeting_note`, `reference`, `glossary`, `contract`, `email`, `technical_doc`, `unknown`
- [ ] Luu `document_type`, `classification_confidence`, `classification_reason`
- [ ] Fallback ve heuristic khi LLM classifier unavailable
- [ ] Cho phep override document type bang tay

Acceptance criteria:
- source moi ingest duoc gan `document_type` hop ly
- neu khong du tin cay thi source duoc gan `unknown` thay vi doan bua

### Workstream 3 - Section Role Detection

Muc tieu:
- gan role nghiep vu cho section/chunk de retrieval va answer assembly biet moi doan dung de lam gi

Files likely touched:
- `backend/app/core/ingest.py`
- `backend/app/models/records.py`
- `backend/app/schemas/source.py`

Checklist:
- [ ] Them `section_role` cho section/chunk
- [ ] Ho tro role theo `sop`
- [ ] Ho tro role theo `policy`
- [ ] Ho tro role theo `report/proposal`
- [ ] Ho tro role theo `glossary/reference`
- [ ] Luu confidence va ly do detect neu can

Acceptance criteria:
- chunk procedural khong chi la text chunk ma biet la `step`, `exception`, `warning`, `prerequisite`
- policy/report chunks duoc nhan role phu hop de rerank va context assembly dung hon

### Workstream 4 - Semantic Unit Chunking

Muc tieu:
- giam cat ngang y va tang chunk utility cho retrieval

Files likely touched:
- `backend/app/core/ingest.py`
- test scripts lien quan den chunking/benchmark

Checklist:
- [ ] Them semantic chunking strategy theo `document_type`
- [ ] SOP chunk theo step/decision/exception unit
- [ ] Policy chunk theo rule/condition/exception/threshold unit
- [ ] Report/proposal chunk theo problem/goal/solution/risk unit
- [ ] Giu lai image/table/list/context gan nhau khi thuoc cung semantic unit
- [ ] Fallback ve structured/window chunking khi khong du signal

Acceptance criteria:
- chunk moi dai vua du, co tinh doc lap, va khong cat dut nghia quan trong
- benchmark retrieval tren tai lieu procedural/policy cai thien so voi chunk mode cu

### Workstream 5 - Parent Section Summary

Muc tieu:
- bo sung context cap section de child chunk nho van retrieve dung nghia lon hon

Files likely touched:
- `backend/app/models/records.py`
- `backend/app/core/ingest.py`
- `backend/app/services/sources.py`
- `backend/app/schemas/source.py`

Checklist:
- [ ] Them concept `source_sections`
- [ ] Them `section_summary`
- [ ] Link child chunks voi parent section
- [ ] Luu heading path / section range / page range phu hop
- [ ] Expose section summary trong source detail va retrieval diagnostics

Acceptance criteria:
- khi retrieve trung child chunk nho, he thong co the mang theo parent section summary
- source detail cho phep debug tu chunk len section va summary cua no

### Workstream 6 - Metadata Enrichment Pipeline

Muc tieu:
- bo sung metadata de candidate scoring va filters co vat lieu that de dung

Files likely touched:
- `backend/app/core/ingest.py`
- `backend/app/models/records.py`
- `backend/app/schemas/source.py`

Checklist:
- [ ] Them `actor`
- [ ] Them `topic`
- [ ] Them `keywords`
- [ ] Them `language`
- [ ] Them `page_number` / page range khi co
- [ ] Them `time_scope` neu detect duoc
- [ ] Dam bao metadata vao chunk, claim, knowledge unit su dung nhat quan

Acceptance criteria:
- retrieval score khong can doan metadata ma co metadata that tu ingest
- source/chunk detail xem duoc metadata phong phu de debug

### Workstream 7 - Phase 2 Regression And Rollout

Muc tieu:
- khoa chat parser/chunker metadata moi truoc khi len phase retrieval object

Files likely touched:
- `backend/scripts/test_phase*.py`
- `backend/scripts/benchmark_retrieval.py`
- `scripts/run_regression.ps1`

Checklist:
- [ ] Them regression cho document-type classification
- [ ] Them regression cho section-role detection
- [ ] Them regression cho semantic chunking
- [ ] Them regression cho parent section summary
- [ ] Cap nhat benchmark retrieval so sanh chunking cu/moi
- [ ] Hook vao `run_regression.ps1`

Acceptance criteria:
- phase 2 co regression rieng va benchmark truoc/sau
- thay doi ingest khong lam vo pipeline cu

### Suggested Commit Order

```text
1. Source metadata foundation
2. Document type classification
3. Section role detection
4. Semantic unit chunking
5. Parent section summary
6. Metadata enrichment pipeline
7. Regression + benchmark
```

### Phase 2 Done Checklist

- [ ] Source metadata authority/status/version/effective date da co
- [ ] Document type da duoc classify va override duoc
- [ ] Section role da duoc gan cho section/chunk
- [ ] Semantic unit chunking da thay the logic cat thuan text o cac doc type chinh
- [ ] Parent section summary da available cho retrieval/debug
- [ ] Metadata enrichment da co trong source detail
- [ ] Regression local pass
- [ ] Frontend build pass
- [ ] Benchmark retrieval lien quan pass

---

## 1.7. Phase 3 Implementation Breakdown

Phan nay tach `Phase 3` thanh cac workstream de mo rong retrieval surface va chuan hoa tri thuc co cau truc.

### Workstream 1 - Retrieval Object Model Foundation

Muc tieu:
- dua cac retrieval object ve mot shape va relation ro rang

Files likely touched:
- `backend/app/models/records.py`
- `backend/app/schemas/source.py`
- `backend/app/schemas/query.py`
- migration moi neu can

Checklist:
- [ ] Chuan hoa `source_sections`
- [ ] Chuan hoa `section_summaries`
- [ ] Chuan hoa `page_summaries`
- [ ] Xac dinh relation giua source/chunk/claim/page/knowledge_unit
- [ ] Chuan hoa ID va provenance link giua object retrieval

Acceptance criteria:
- moi retrieval object truy duoc ve source evidence goc
- candidate shape co the dung chung qua nhieu object type

### Workstream 2 - Knowledge Units Normalization

Muc tieu:
- bien knowledge units thanh object retrieval co cau truc that su huu dung

Files likely touched:
- `backend/app/models/records.py`
- `backend/app/core/ingest.py`
- `backend/app/services/sources.py`
- `backend/app/api/sources.py`

Checklist:
- [ ] Chuan hoa `unit_type`
- [ ] Ho tro unit type: `definition`, `rule`, `procedure_step`, `condition`, `exception`, `threshold`, `warning`, `decision`, `relationship`, `example`
- [ ] Luu `source_ids`, `chunk_ids`, `entities`, `confidence`, `verification_status`
- [ ] Gan metadata authority/provenance vao knowledge unit neu can
- [ ] Expose knowledge units ro hon trong source detail/API

Acceptance criteria:
- knowledge unit khong con chi la artifact semantic chung chung
- Ask AI co the retrieve unit theo intent va unit type

### Workstream 3 - Page Summary Retrieval Surface

Muc tieu:
- dung page-level summaries de tra loi definition/overview nhanh hon raw chunk only

Files likely touched:
- `backend/app/services/pages.py`
- `backend/app/services/query.py`
- `backend/app/models/records.py`

Checklist:
- [ ] Chuan hoa summary ngan cho moi page
- [ ] Luu summary quality/provenance neu can
- [ ] Them retrieval policy uu tien page summary voi query overview/summary/definition
- [ ] Link page summary ve page slug/source ids

Acceptance criteria:
- query tong quan khong phai luc nao cung can day raw chunk vao answer
- page summaries co provenance ro rang va khong mat lien ket voi source

### Workstream 4 - Multi-object Retrieval Engine

Muc tieu:
- retrieve dong thoi tren nhieu object type va score trong mot pipeline chung

Files likely touched:
- `backend/app/services/query.py`
- `backend/app/core/embedding_client.py`
- `backend/app/core/runtime_config.py`

Checklist:
- [ ] Them retrieval branch cho `claims`
- [ ] Them retrieval branch cho `section summaries`
- [ ] Them retrieval branch cho `page summaries`
- [ ] Them retrieval branch cho `knowledge_units`
- [ ] Chuan hoa candidate scoring giua object types
- [ ] Them object-specific boost theo intent

Acceptance criteria:
- he thong co the retrieve object dung loai voi y dinh cau hoi
- diagnostics chi ro candidate den tu object type nao va vi sao duoc chon

### Workstream 5 - Intent-specific Retrieval Policy

Muc tieu:
- khong dung mot retrieval policy chung cho moi loai cau hoi

Files likely touched:
- `backend/app/services/query.py`
- regression/eval scripts lien quan

Checklist:
- [ ] Definition -> uu tien glossary/definition unit/page summary
- [ ] Procedure -> uu tien procedure_step/section summary/chunk step
- [ ] Policy -> uu tien rule/condition/exception/threshold
- [ ] Comparison -> can evidence cho ca hai ben
- [ ] Conflict -> uu tien claims + authority metadata + latest approved sources
- [ ] Source lookup -> uu tien page/source metadata va provenance

Acceptance criteria:
- retrieval policy thay doi theo intent thay vi top-k chung
- context assembly nhan duoc candidate da co stratification theo intent

### Workstream 6 - Provenance And Citation Graph

Muc tieu:
- dam bao moi retrieval object dan nguoc duoc ve chunk/source goc

Files likely touched:
- `backend/app/models/records.py`
- `backend/app/services/query.py`
- `backend/app/services/pages.py`
- `backend/app/schemas/query.py`

Checklist:
- [ ] Link `knowledge_unit -> chunk/source`
- [ ] Link `page_summary -> page -> source`
- [ ] Link `section_summary -> section -> child_chunks`
- [ ] Them citation payload cho object khong phai chunk
- [ ] Dam bao UI van mo duoc source evidence tu object da retrieve

Acceptance criteria:
- khong co retrieval object "mo côi" khong trace ve source goc
- citation panel va debug panel van giu duoc provenance ro rang

### Workstream 7 - Phase 3 Regression And Benchmark

Muc tieu:
- khoa chat multi-object retrieval truoc khi di sau sang eval phase day du

Files likely touched:
- `backend/scripts/test_phase*.py`
- `backend/scripts/benchmark_retrieval.py`
- `scripts/run_regression.ps1`

Checklist:
- [ ] Them regression cho query definition
- [ ] Them regression cho query procedure
- [ ] Them regression cho query policy/conflict
- [ ] Them regression cho multi-object provenance
- [ ] Them benchmark precision theo object type

Acceptance criteria:
- retrieval object moi co regression rieng
- benchmark cho thay object-type retrieval huu ich hon raw chunk only

### Suggested Commit Order

```text
1. Retrieval object model foundation
2. Knowledge units normalization
3. Page summary retrieval surface
4. Multi-object retrieval engine
5. Intent-specific retrieval policy
6. Provenance and citation graph
7. Regression + benchmark
```

### Phase 3 Done Checklist

- [ ] `source_sections`, `section_summaries`, `page_summaries` da chuan hoa
- [ ] `knowledge_units` da co schema va provenance dung duoc
- [ ] Retrieval da ho tro nhieu object type trong pipeline chung
- [ ] Intent-specific policy da anh huong den candidate selection
- [ ] Provenance/citation cho object moi van mo duoc ve source goc
- [ ] Regression local pass
- [ ] Benchmark retrieval lien quan pass

---

## 1.8. Phase 4 Implementation Breakdown

Phan nay tach `Phase 4` thanh cac workstream de do luong, benchmark, va dat quality gate cho toan pipeline.

### Workstream 1 - Eval Dataset Foundation

Muc tieu:
- tao bo eval on dinh de do retrieval va answer quality

Files likely touched:
- `backend/app/models/records.py`
- `backend/scripts/*eval*`
- migration moi neu can

Checklist:
- [ ] Them model hoac file store cho `eval_cases`
- [ ] Ho tro `question`, `chat_history`, `collection_id`, `expected_sources`, `expected_chunks`, `expected_behavior`
- [ ] Seed bo case toi thieu cho follow-up, ambiguity, conflict, insufficient evidence, source lookup
- [ ] Co helper import/export eval cases

Acceptance criteria:
- co bo eval co the chay lap lai nhieu lan
- case cover du nhom loi quan trong cua Ask AI

### Workstream 2 - Eval Runner

Muc tieu:
- chay hang loat case va luu lai metrics/debug cho moi lan run

Files likely touched:
- `backend/scripts/*eval*`
- `backend/app/api/*` neu expose endpoint
- `backend/app/models/records.py`

Checklist:
- [ ] Them `eval_runs`
- [ ] Chay tung case qua Ask pipeline that
- [ ] Luu output, retrieval debug, answer, va metrics cho moi case
- [ ] Ho tro run full set hoac subset theo tag

Acceptance criteria:
- moi run co ID, config, metrics, va artifacts debug co the doc lai
- eval runner dung duoc cho local va CI/regression script

### Workstream 3 - Metrics Layer

Muc tieu:
- do dung thu can do thay vi chi do score tong quan

Files likely touched:
- `backend/scripts/*eval*`
- `backend/app/core/reliability.py`

Checklist:
- [ ] Them `retrieval_recall@5`
- [ ] Them `retrieval_recall@10`
- [ ] Them `rerank_precision@5`
- [ ] Them `citation_precision`
- [ ] Them `answer_faithfulness`
- [ ] Them `unsupported_claim_rate`
- [ ] Them `followup_resolution_success`
- [ ] Them `conflict_handling_accuracy`
- [ ] Them `clarification_accuracy`

Acceptance criteria:
- metrics tach ro retrieval, rerank, grounding, va behavior
- co baseline de so sanh qua tung thay doi retrieval/prompt

### Workstream 4 - Quality Gates And Lint Extensions

Muc tieu:
- bien eval thanh gate va bo sung quality checks lien quan authority/staleness/conflict

Files likely touched:
- `backend/app/api/lint.py`
- `backend/app/services/*lint*`
- `backend/scripts/run_regression.ps1`

Checklist:
- [ ] Them check unsupported claims cho Ask answer khi can
- [ ] Them check stale source citation
- [ ] Them check authority mismatch
- [ ] Them threshold gate cho benchmark quan trong
- [ ] Neu metrics rot threshold thi regression script phai fail ro rang

Acceptance criteria:
- retrieval/answer changes khong the merge am tham khi metrics giam manh
- conflict va authority issues co quality gate rieng

### Workstream 5 - Admin Eval And Debug Surface

Muc tieu:
- cho admin xem benchmark va truy vet ca case sai

Files likely touched:
- `llm-wiki/src/app/(main)/admin/*`
- `llm-wiki/src/app/(main)/ask/*`
- frontend types/services lien quan

Checklist:
- [ ] Hien tong quan eval runs
- [ ] Hien metrics chinh theo run
- [ ] Hien failed cases va retrieval debug cua tung case
- [ ] Link tu failed case den source/page evidence lien quan

Acceptance criteria:
- admin khong can doc log thô de biet retrieval dang hong o dau
- failed cases truy vet duoc den query rewrite, candidate selection, rerank, answer output

### Workstream 6 - Automation And Release Checklist

Muc tieu:
- dua eval/benchmark vao quy trinh regression phat trien thong thuong

Files likely touched:
- `scripts/run_regression.ps1`
- `README.md`
- `UPDATE_PLAN_2.md` hoac plan lien quan khi rollout

Checklist:
- [ ] Them benchmark/eval command vao regression script
- [ ] Ghi huong dan chay eval vao README/doc
- [ ] Dinh nghia checklist release co benchmark before/after
- [ ] Cap nhat plan status khi phase verified

Acceptance criteria:
- eval va benchmark tro thanh mot phan cua quy trinh thay doi retrieval
- tai lieu van hanh/release co huong dan ro rang

### Suggested Commit Order

```text
1. Eval dataset foundation
2. Eval runner
3. Metrics layer
4. Quality gates and lint extensions
5. Admin eval/debug surface
6. Automation and release checklist
```

### Phase 4 Done Checklist

- [ ] Eval dataset co bo case co dinh va import/export duoc
- [ ] Eval runner luu run + metrics + debug artifacts
- [ ] Metrics retrieval/rerank/faithfulness/clarification da co
- [ ] Quality gate da noi vao regression
- [ ] Admin xem duoc failed cases va debug detail
- [ ] Regression local pass
- [ ] Benchmark/eval pass theo threshold da dat

---

## 2. Phase 1 — Fix Ask AI trước

Đây là phase nên làm đầu tiên vì nó tác động trực tiếp tới lỗi user thấy hằng ngày.

---

### 2.1. Conversational Query Rewrite

#### Vấn đề hiện tại

User thường hỏi kiểu:

```text
cái trên là gì?
so sánh 2 cái này
ý tôi là phần điều kiện
trả lời sai rồi
nó áp dụng khi nào?
```

Nếu chỉ lấy câu cuối để retrieve thì hệ thống dễ lấy sai chunk.

#### Giải pháp

Trước retrieval, tạo một bước:

```text
raw_user_question + recent_chat_history
→ standalone_query
→ intent
→ expected_answer_type
→ filters
```

#### Output mong muốn

```json
{
  "standalone_query": "Điều kiện áp dụng National Account Relationship trong tài liệu hướng dẫn Epicor là gì?",
  "intent": "procedure",
  "answer_type": "step_by_step",
  "target_entities": ["National Account Relationship", "Epicor"],
  "filters": {
    "document_type": "sop",
    "collection_id": "..."
  },
  "needs_clarification": false,
  "clarification_question": null
}
```

#### Intent cần detect

```text
fact_lookup
definition
summary
procedure
comparison
policy_rule
threshold
timeline
issue_status
correction_followup
ambiguous_followup
conflict_check
source_lookup
```

#### Logic

Nếu query quá mơ hồ:

```text
“cái đó thì sao?”
“nó là gì?”
“so sánh cái này”
```

và chat history không đủ resolve → **hỏi lại**, không retrieve bừa.

---

### 2.2. Chat History Aware Retrieval

#### Vấn đề

Ask AI hiện có thể không hiểu context từ câu trước.

#### Giải pháp

Dùng 3-5 lượt chat gần nhất để:

- resolve pronoun: cái này, cái đó, nó
- xác định entity đang nói
- xác định source/page đang mở
- xác định collection scope

#### Context nên đưa vào retrieval

```json
{
  "current_page_id": "...",
  "current_collection_id": "...",
  "recent_entities": ["Epicor", "National Account Relationship"],
  "recent_sources": ["source_123"],
  "conversation_summary": "User is asking about setup steps and conditions for National Account Relationship."
}
```

---

### 2.3. Multi-source Candidate Retrieval

#### Hiện tại

```text
query → chunks → top N
```

#### Nên nâng thành

```text
query → retrieve candidates from:
1. source_chunks
2. section_summaries
3. claims
4. page_summaries
5. knowledge_units
6. glossary_terms
7. entities
```

#### Vì sao?

Ví dụ user hỏi:

```text
Credit Limit là gì?
```

Có thể glossary trả lời tốt hơn raw chunk.

User hỏi:

```text
Quy trình thiết lập National Account Relationship gồm mấy bước?
```

SOP page summary + chunks theo step sẽ tốt hơn glossary.

User hỏi:

```text
Có claim nào chưa có nguồn không?
```

Retrieve từ claims/lint results tốt hơn source chunks.

---

### 2.4. Candidate Retrieval Strategy

Nên làm retrieval theo 2 tầng.

#### Tầng A — Recall rộng

Lấy top 30-50 candidates.

```text
lexical search
+ vector search
+ metadata filter
+ page/source relation boost
```

#### Tầng B — Rerank hẹp

Rerank còn top 5-10 evidence tốt nhất.

---

### 2.5. Scoring đề xuất

Mỗi candidate nên có score tổng hợp:

```text
final_score =
  semantic_score * 0.35
+ lexical_score * 0.20
+ metadata_match_score * 0.15
+ authority_score * 0.10
+ freshness_score * 0.10
+ citation_verified_score * 0.10
```

Không nhất thiết phải đúng tuyệt đối, nhưng nên có logic rõ.

#### Metadata match score

Boost nếu:

```text
document_type khớp intent
section_role khớp answer_type
collection khớp current scope
entity khớp target_entities
language khớp query
```

---

### 2.6. Reranking

#### Option nhanh

Dùng LLM reranker.

Prompt rerank:

```text
Given the user question and candidate passages, score each passage from 0-5.

Criteria:
- Directly answers the question
- Contains evidence, not just related topic
- Has correct scope
- Is specific enough
- Avoids irrelevant similar terms
- Has usable citation

Return JSON only.
```

#### Output

```json
[
  {
    "candidate_id": "chunk_123",
    "score": 4.8,
    "reason": "Directly explains the setup purpose and credit limit behavior."
  },
  {
    "candidate_id": "claim_456",
    "score": 4.1,
    "reason": "Supports the key condition but lacks procedure detail."
  }
]
```

#### Option tốt hơn về sau

Dùng reranker model chuyên dụng hoặc embedding rerank service.

---

### 2.7. Context Assembly theo coverage

#### Vấn đề

Không nên nhét top 4 chunks na ná nhau.

#### Cách mới

Dựa trên intent để build context.

Ví dụ với `procedure`:

```text
context should include:
- purpose/scope
- prerequisites
- steps
- exceptions
- warnings
```

Ví dụ với `policy_rule`:

```text
context should include:
- rule
- scope
- condition
- threshold
- exception
- effective date
```

Ví dụ với `comparison`:

```text
context should include:
- evidence for object A
- evidence for object B
- common criteria
- difference table
```

#### Output context nên có format

```json
{
  "context_pack": [
    {
      "role": "definition",
      "source_id": "source_1",
      "chunk_id": "chunk_1",
      "text": "..."
    },
    {
      "role": "procedure_step",
      "source_id": "source_1",
      "chunk_id": "chunk_2",
      "text": "..."
    },
    {
      "role": "exception",
      "source_id": "source_1",
      "chunk_id": "chunk_3",
      "text": "..."
    }
  ],
  "coverage": {
    "has_definition": true,
    "has_steps": true,
    "has_exception": false
  }
}
```

---

### 2.8. Answer Generation Schema

#### Bắt buộc answer theo 3 lớp

```text
1. Direct Answer
2. Evidence / Sources
3. Uncertainty / Missing Evidence
```

#### Nếu có suy luận

Phải tách riêng:

```text
Inference:
Dựa trên source A và source B, có thể hiểu rằng...
```

Không được viết như fact chắc chắn.

#### Nếu thiếu evidence

Trả lời:

```text
Tôi chưa thấy đủ bằng chứng trong tài liệu đã index để kết luận.
Tài liệu hiện chỉ nói ...
```

#### Nếu conflict

Trả lời:

```text
Có 2 nguồn đang mâu thuẫn:

Nguồn A nói ...
Nguồn B nói ...

Chưa thể kết luận nếu không có rule ưu tiên version/latest/approved.
```

---

## 3. Phase 2 — Nâng ingest để retrieval tốt hơn

Phase này giúp nền tảng mạnh hơn, nhất là khi tài liệu lớn dần.

---

### 3.1. Document Type Classification

Không chỉ phân theo file type `.pdf`, `.docx`, `.txt`.

Cần phân theo **content type**:

```text
sop
policy
report
proposal
meeting_note
reference
glossary
contract
email
technical_doc
unknown
```

#### Prompt classify

```text
Classify this document by content purpose, not file extension.

Allowed types:
- sop
- policy
- report
- proposal
- meeting_note
- reference
- glossary
- contract
- email
- technical_doc
- unknown

Return JSON:
{
  "document_type": "...",
  "confidence": 0-1,
  "reason": "...",
  "detected_signals": []
}
```

---

### 3.2. Section Role Detection

Mỗi section/chunk nên có `section_role`.

#### Với SOP

```text
purpose
scope
prerequisite
step
decision
exception
warning
troubleshooting
output
```

#### Với Policy

```text
rule
scope
condition
threshold
exception
responsibility
approval
deadline
penalty
```

#### Với Report/Proposal

```text
problem
background
current_state
goal
solution
benefit
risk
timeline
cost
recommendation
action_item
```

#### Với Glossary/Reference

```text
term
definition
example
note
related_term
```

---

### 3.3. Semantic Unit Chunking

#### Không nên chunk kiểu quá đơn giản

```text
1000 tokens mỗi chunk
```

Vì sẽ cắt ngang ý.

#### Nên chunk theo semantic unit

Ví dụ SOP:

```text
Step 1 + screenshot + warning liên quan = 1 semantic unit
```

Policy:

```text
Rule + condition + exception = 1 semantic unit
```

Report:

```text
Problem + impact = 1 unit
Solution + benefit = 1 unit
Risk + mitigation = 1 unit
```

---

### 3.4. Parent Chunk / Section Summary

#### Model dữ liệu

```text
source
  → section
    → section_summary
      → child_chunks
```

#### Vì sao cần?

Khi retrieve trúng chunk nhỏ:

```text
“Nhấn nút Selected”
```

nó không đủ hiểu đang nằm trong quy trình nào.

Parent summary sẽ giúp:

```text
Đây là bước chọn Parent's Credit để chuyển từ Available sang Selected trong cấu hình National Account Relationship.
```

---

### 3.5. Metadata Enrichment

Mỗi chunk nên lưu:

```json
{
  "document_type": "sop",
  "section_role": "step",
  "actor": "admin",
  "time_scope": null,
  "topic": "National Account Relationship",
  "keywords": ["Credit Limit", "Parent", "Child", "Selected"],
  "language": "vi",
  "page_number": 3,
  "section_title": "Setup National Account Relationship",
  "source_status": "uploaded",
  "authority_level": "reference",
  "effective_date": null,
  "version": "v2"
}
```

---

## 4. Phase 3 — Knowledge Units

### 4.1. Vì sao cần Knowledge Units?

Raw chunk là text.  
Claim là câu khẳng định.  
Page là content dài.

Còn `knowledge_unit` là một mảnh tri thức có cấu trúc.

Ví dụ:

```json
{
  "unit_type": "procedure_step",
  "title": "Move Parent's Credit to Selected",
  "content": "Use the arrow button to move Parent's Credit from Available to Selected.",
  "source_ids": ["source_123"],
  "chunk_ids": ["chunk_456"],
  "entities": ["Parent's Credit", "Credit Limit"],
  "confidence": 0.87
}
```

### 4.2. Các loại knowledge unit

```text
definition
rule
procedure_step
condition
exception
threshold
warning
decision
relationship
example
```

### 4.3. Ask AI dùng knowledge units thế nào?

Nếu hỏi định nghĩa:

```text
retrieve glossary_terms + definition units
```

Nếu hỏi quy trình:

```text
retrieve procedure_step units + section summary
```

Nếu hỏi điều kiện:

```text
retrieve condition/rule/exception units
```

---

## 5. Phase 4 — Source Priority / Authority Ranking

### 5.1. Vấn đề

Tài liệu nội bộ thường có nhiều nguồn:

```text
draft
approved policy
meeting note
email
manual note
old version
new version
```

Nếu không có authority ranking, AI có thể lấy sai nguồn.

### 5.2. Metadata cần thêm cho source

```text
source_status: draft | approved | archived | unknown
authority_level: official | reference | informal | user_note
effective_date
version
owner
uploaded_by
approved_by
created_at
updated_at
```

### 5.3. Rule ưu tiên

Ví dụ:

```text
approved policy > approved SOP > reference doc > meeting note > manual note > draft
new version > old version
same collection > external collection
verified citation > unverified
```

Khi conflict, answer phải nói:

```text
Source A có authority cao hơn vì là approved policy và mới hơn.
Source B chỉ là meeting note nên nên dùng để tham khảo.
```

---

## 6. Phase 5 — Eval Set & Benchmark

### 6.1. Vì sao cần?

Không có eval thì không biết nâng cấp có tốt thật không.

### 6.2. Tạo bộ câu hỏi nội bộ

Bắt đầu với 50 câu.

Nhóm câu hỏi:

```text
1. factual lookup
2. definition
3. SOP procedural
4. policy threshold
5. compare two documents
6. ambiguous follow-up
7. correction follow-up
8. conflict detection
9. insufficient evidence
10. source lookup
```

### 6.3. Schema eval case

```json
{
  "id": "eval_001",
  "question": "Credit Limit trong National Account Relationship là gì?",
  "chat_history": [],
  "collection_id": "collection_epicor",
  "expected_answer": "Credit Limit là tổng hạn mức tín dụng mà cả tập đoàn được phép sử dụng...",
  "expected_sources": ["source_123"],
  "expected_chunk_ids": ["chunk_456"],
  "expected_behavior": "answer",
  "tags": ["definition", "epicor", "glossary"]
}
```

### 6.4. Expected behavior

```text
answer
ask_clarification
insufficient_evidence
show_conflict
compare
summarize
```

### 6.5. Metrics

```text
retrieval_recall@5
retrieval_recall@10
rerank_precision@5
citation_precision
answer_faithfulness
unsupported_claim_rate
followup_resolution_success
conflict_handling_accuracy
clarification_accuracy
```

### 6.6. Benchmark command

Nên có script:

```bash
npm run eval:rag
```

Output:

```text
Total cases: 50
Retrieval recall@5: 82%
Citation precision: 76%
Faithfulness: 88%
Unsupported claim rate: 9%
Conflict handling: 70%
```

---

## 7. Database Schema đề xuất

### 7.1. `sources`

```sql
sources (
  id uuid primary key,
  collection_id uuid,
  title text,
  file_type text,
  document_type text,
  source_status text,
  authority_level text,
  language text,
  version text,
  effective_date date,
  owner text,
  file_path text,
  extracted_text text,
  created_at timestamp,
  updated_at timestamp
)
```

### 7.2. `source_sections`

```sql
source_sections (
  id uuid primary key,
  source_id uuid,
  parent_section_id uuid null,
  title text,
  section_role text,
  summary text,
  order_index int,
  page_start int,
  page_end int,
  created_at timestamp
)
```

### 7.3. `source_chunks`

```sql
source_chunks (
  id uuid primary key,
  source_id uuid,
  section_id uuid,
  content text,
  chunk_type text,
  section_role text,
  document_type text,
  actor text,
  topic text,
  keywords jsonb,
  language text,
  page_number int,
  token_count int,
  embedding vector,
  created_at timestamp
)
```

### 7.4. `claims`

```sql
claims (
  id uuid primary key,
  source_id uuid,
  chunk_id uuid,
  claim_text text,
  claim_type text,
  entities jsonb,
  confidence numeric,
  verification_status text,
  created_at timestamp
)
```

### 7.5. `knowledge_units`

```sql
knowledge_units (
  id uuid primary key,
  collection_id uuid,
  unit_type text,
  title text,
  content text,
  source_ids jsonb,
  chunk_ids jsonb,
  entities jsonb,
  confidence numeric,
  verification_status text,
  embedding vector,
  created_at timestamp,
  updated_at timestamp
)
```

### 7.6. `pages`

```sql
pages (
  id uuid primary key,
  collection_id uuid,
  title text,
  slug text,
  page_type text,
  origin text,
  content_md text,
  summary text,
  status text,
  citation_state text,
  confidence_score numeric,
  last_generated_at timestamp,
  last_reviewed_at timestamp,
  created_at timestamp,
  updated_at timestamp
)
```

### 7.7. `citations`

```sql
citations (
  id uuid primary key,
  page_id uuid,
  claim_id uuid null,
  source_id uuid,
  chunk_id uuid,
  quote text,
  page_number int,
  confidence numeric,
  created_at timestamp
)
```

### 7.8. `retrieval_logs`

```sql
retrieval_logs (
  id uuid primary key,
  user_question text,
  standalone_query text,
  intent text,
  retrieved_candidates jsonb,
  reranked_candidates jsonb,
  selected_context jsonb,
  answer_id uuid,
  created_at timestamp
)
```

### 7.9. `eval_cases`

```sql
eval_cases (
  id uuid primary key,
  question text,
  chat_history jsonb,
  collection_id uuid,
  expected_answer text,
  expected_sources jsonb,
  expected_chunks jsonb,
  expected_behavior text,
  tags jsonb,
  created_at timestamp
)
```

### 7.10. `eval_runs`

```sql
eval_runs (
  id uuid primary key,
  run_name text,
  config jsonb,
  metrics jsonb,
  created_at timestamp
)
```

---

## 8. API Design

### 8.1. Ask AI endpoint

```http
POST /api/ask
```

Request:

```json
{
  "question": "Credit Limit là gì?",
  "collection_id": "collection_123",
  "page_id": null,
  "chat_history": [
    {
      "role": "user",
      "content": "National Account Relationship là gì?"
    },
    {
      "role": "assistant",
      "content": "..."
    }
  ]
}
```

Response:

```json
{
  "answer": "...",
  "answer_type": "definition",
  "evidence": [
    {
      "source_id": "source_123",
      "chunk_id": "chunk_456",
      "quote": "...",
      "page_number": 2
    }
  ],
  "uncertainty": "Không thấy thông tin về ngày hiệu lực trong tài liệu.",
  "inference_used": false,
  "conflicts": [],
  "retrieval_debug_id": "log_123"
}
```

---

### 8.2. Query rewrite endpoint

```http
POST /api/ask/rewrite
```

Response:

```json
{
  "standalone_query": "...",
  "intent": "procedure",
  "answer_type": "step_by_step",
  "needs_clarification": false,
  "filters": {}
}
```

---

### 8.3. Retrieval endpoint

```http
POST /api/retrieval/candidates
```

---

### 8.4. Rerank endpoint

```http
POST /api/retrieval/rerank
```

---

### 8.5. Eval endpoint

```http
POST /api/eval/run
```

---

## 9. Ask AI Flow chi tiết

### Step 1 — Receive user query

```text
question + chat_history + current_page + current_collection
```

### Step 2 — Query Understanding

Generate:

```text
standalone_query
intent
target_entities
filters
needs_clarification
```

Nếu `needs_clarification = true`, trả về câu hỏi lại.

### Step 3 — Retrieve Candidates

Retrieve từ nhiều table:

```text
source_chunks
section_summaries
claims
knowledge_units
page_summaries
glossary_terms
entities
```

### Step 4 — Rerank

Input top 30-50 → output top 5-10.

### Step 5 — Context Assembly

Dựa vào intent:

```text
definition → definition + examples + source
procedure → purpose + steps + exceptions
comparison → evidence A + evidence B
policy → rule + scope + threshold + exception
```

### Step 6 — Generate Answer

Answer format:

```text
Direct Answer
Evidence
Uncertainty
```

### Step 7 — Grounding Check

Check answer:

```text
mỗi claim trong answer có evidence không?
có câu nào unsupported không?
có conflict không?
```

### Step 8 — Return Answer + Evidence

---

## 10. Prompt Templates

### 10.1. Query Rewrite Prompt

```text
You are a query understanding module for a document QA system.

Given:
- user question
- recent chat history
- current page context
- current collection context

Your job:
1. Rewrite the user question into a standalone query.
2. Detect intent.
3. Detect whether clarification is needed.
4. Suggest metadata filters if appropriate.

Return JSON only:
{
  "standalone_query": "...",
  "intent": "...",
  "answer_type": "...",
  "target_entities": [],
  "filters": {},
  "needs_clarification": false,
  "clarification_question": null
}

Rules:
- If the question is ambiguous and chat history cannot resolve it, set needs_clarification = true.
- Do not invent entities.
- Preserve the user's language.
```

---

### 10.2. Reranker Prompt

```text
You are a reranking module for a grounded document QA system.

Question:
{{question}}

Candidates:
{{candidates}}

Score each candidate from 0 to 5 based on:
- direct relevance
- answerability
- evidence strength
- scope match
- citation usefulness
- whether it contains the actual answer, not just related words

Return JSON:
[
  {
    "candidate_id": "...",
    "score": 0-5,
    "reason": "..."
  }
]
```

---

### 10.3. Context Assembly Prompt

```text
You are assembling context for a grounded answer.

Question:
{{question}}

Intent:
{{intent}}

Reranked candidates:
{{candidates}}

Select a compact context pack that covers the answer.

Rules:
- Avoid duplicate candidates saying the same thing.
- Prefer evidence with citations.
- Include parent section summary if a child chunk needs context.
- For procedure questions, include purpose, steps, exceptions if available.
- For policy questions, include rule, condition, threshold, exception if available.
- For comparison questions, include evidence for both sides.

Return JSON:
{
  "context_pack": [],
  "coverage": {},
  "missing_evidence": []
}
```

---

### 10.4. Answer Generation Prompt

```text
You are a grounded answer assistant for an internal knowledge base.

Use only the provided evidence unless explicitly marking an inference.

Question:
{{question}}

Context:
{{context_pack}}

Instructions:
1. Give a direct answer first.
2. Cite evidence for key claims.
3. If evidence is incomplete, say what is missing.
4. If sources conflict, present the conflict instead of merging them.
5. Separate grounded facts from inference.
6. Do not invent facts.

Return:
{
  "direct_answer": "...",
  "evidence": [],
  "inference": null,
  "uncertainty": null,
  "conflicts": [],
  "follow_up_needed": null
}
```

---

## 11. Implementation Roadmap

### Sprint 1 — Ask AI Query Understanding

Deliverables:

- query rewrite service
- intent detection
- chat history resolver
- ambiguous query handling
- retrieval logs

Impact:

```text
fix lỗi follow-up
fix lỗi “cái đó”, “ý tôi là”
giảm retrieve bừa
```

---

### Sprint 2 — Multi-source Retrieval + Rerank

Deliverables:

- retrieve từ chunks + claims + page summaries
- LLM reranker
- top 30-50 recall, top 5-10 final
- metadata filter

Impact:

```text
tìm đúng evidence hơn
giảm answer lệch do top chunk sai
```

---

### Sprint 3 — Context Assembly + Answer Guardrails

Deliverables:

- context assembly by intent
- direct answer / evidence / uncertainty format
- conflict handling
- unsupported claim check

Impact:

```text
answer đáng tin hơn
citation rõ hơn
ít hallucination hơn
```

---

### Sprint 4 — Document Type Aware Ingest

Deliverables:

- document type classifier
- section role detection
- parent section summary
- enriched chunk metadata

Impact:

```text
retrieval chất lượng hơn trên tài liệu lớn
chunk có ngữ cảnh hơn
```

---

### Sprint 5 — Knowledge Units

Deliverables:

- extract knowledge_units
- index knowledge_units
- retrieve by unit type
- link units to pages/sources/chunks

Impact:

```text
Ask AI trả lời tốt hơn cho procedure/rule/definition
wiki page generation tốt hơn
```

---

### Sprint 6 — Eval & Benchmark

Deliverables:

- eval_cases table
- eval runner
- fixed benchmark dataset
- metrics dashboard

Impact:

```text
đo được cải thiện thật
tránh sửa prompt/retrieval theo cảm giác
```

---

## 12. Practical Priority

Nếu cần làm nhanh, ưu tiên thứ tự:

```text
1. Conversational query rewrite
2. Chat history aware retrieval
3. Rerank top candidates
4. Context assembly theo coverage
5. Answer schema + uncertainty/conflict
6. Retrieve thêm claims + page summaries
7. Document-type-aware chunking
8. Parent chunk / section summary
9. Knowledge units
10. Eval set
```

---

## 13. Expected Impact

### Fix nhanh nhất

```text
Conversational query rewrite
Chat history retrieval
Reranking
Context assembly
```

Sẽ cải thiện ngay các lỗi:

```text
không hiểu follow-up
lấy sai chunk
trả lời lệch ý
nhét context trùng lặp
```

### Nâng nền tốt nhất

```text
document-type-aware chunking
section summary
knowledge units
eval set
```

Sẽ giúp hệ thống tốt hơn khi:

```text
tài liệu nhiều lên
chủ đề phức tạp hơn
có nhiều version/source
cần trả lời có citation chính xác
```

---

## 14. Risk & Edge Cases

### 14.1. Query rewrite sai

Nếu rewrite sai, retrieval sẽ sai toàn bộ.

Giải pháp:

```text
log standalone_query
hiển thị debug cho admin
cho user thấy “I interpreted your question as...”
```

---

### 14.2. Reranker chọn sai vì prompt yếu

Giải pháp:

```text
store rerank reason
compare against eval set
cho rerank score minh bạch trong debug mode
```

---

### 14.3. Metadata classifier sai

Giải pháp:

```text
confidence threshold
document_type = unknown nếu không chắc
cho user sửa document type thủ công
```

---

### 14.4. Conflict giữa source

Giải pháp:

```text
source authority ranking
effective date
version
approved/draft status
```

---

### 14.5. Too much context

Giải pháp:

```text
context assembly theo coverage
deduplicate candidates
parent summary ngắn
evidence quote compact
```

---

## 15. Checklist triển khai

### Backend

- [ ] Add query rewrite service
- [ ] Add intent detection
- [ ] Add retrieval logs
- [ ] Add multi-source retrieval
- [ ] Add reranker
- [ ] Add context assembly
- [ ] Add answer schema
- [ ] Add conflict detection
- [ ] Add source authority metadata
- [ ] Add eval runner

### Ingest

- [ ] Document type classifier
- [ ] Section role classifier
- [ ] Semantic unit chunking
- [ ] Parent section summary
- [ ] Metadata enrichment
- [ ] Knowledge unit extraction

### Frontend

- [ ] Ask AI shows interpreted query
- [ ] Evidence panel
- [ ] Uncertainty display
- [ ] Conflict display
- [ ] Retrieval debug mode for admin
- [ ] Eval dashboard
- [ ] Source authority indicators

### Quality

- [ ] Eval cases
- [ ] Retrieval recall metric
- [ ] Citation precision metric
- [ ] Faithfulness metric
- [ ] Unsupported claim rate
- [ ] Regression test for Ask AI

---

## 16. Kết luận

Không nên chỉ tăng model hoặc tăng top-k retrieval.

Hướng đúng là nâng toàn pipeline theo 4 lớp:

```text
1. Ingest hiểu cấu trúc hơn
2. Retrieval đa tầng và có rerank
3. Answer generation có provenance/guardrail
4. Eval set để đo chất lượng
```

Thứ tự triển khai tốt nhất:

```text
Fix Ask AI trước
→ Nâng ingest
→ Thêm knowledge units
→ Thêm eval benchmark
```

Kỳ vọng:

```text
hệ thống hiểu follow-up tốt hơn
tìm đúng evidence hơn
trả lời bám nguồn hơn
ít hallucination hơn
dễ debug hơn
cải thiện có thể đo được bằng benchmark
```
