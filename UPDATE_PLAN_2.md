# LLM Wiki Upgrade Plan 2

Roadmap nay tiep noi `UPDATE_PLAN.md`, dua tren gap con lai giua code hien tai va target trong `hybrid-rag-karpathy-llm-wiki-prompts.md` / `llm_wiki_product_spec_vi.md`.

## Quick Status

| Scope | Status | Verified On |
|---|---|---|
| Phase 6-12 | Done | backend scripts, frontend build, historical Docker smoke |
| Phase 13-17 | Done | backend scripts, frontend build, Docker smoke/eval |
| Phase 18 | Done | Playwright smoke, `e2e_smoke.ps1`, Docker smoke |
| Phase 19-21 | Done | backend scripts, frontend build, admin/auth regression |
| Phase 22 | Done | full regression script, Docker smoke, E2E smoke |
| Phase 23-27 | Done | diagram regression scripts, frontend build, Docker smoke |
| Phase 28 | Done | Docker/runtime with Tesseract; local host may skip if `tesseract` is absent |
| Phase 29-32 | Done | backend scripts, compileall, frontend build, Docker smoke |
| Ad-hoc: Ask chat history | Done | backend script, frontend build, Docker smoke |
| Current overall state | Verified | local regression PASS, Docker rebuild PASS, Docker smoke PASS, E2E smoke PASS on 2026-05-04 |

## Verification Format

- `Implementation log`: code and behavior that were added.
- `Verification`: the shortest reliable summary of how that phase was confirmed.
- `PASS on Docker/runtime` va `skip on local` co the cung dung voi phase co dependency he thong nhu `tesseract`.

## Phase 6: Collections And Source Organization

Muc tieu:
- bien collections thanh first-class object thay vi chi la UI grouping
- ho tro upload source khong can chon dung page, nhung van de xuat collection/page lien quan
- mo duong cho graph/source/page filter theo collection

Checklist:
- [x] Them schema/model `collections`
- [x] Them `collection_id` cho `sources` va optional `pages`
- [x] Seed demo collections
- [x] Them Collections API: list/get/create/update/delete
- [x] Them API gan source/page vao collection
- [x] Them auto-detect collection suggestion khi ingest source
- [x] Them Collection View trong UI
- [x] Nang sidebar/page tree de browse theo collection
- [x] Them filter collection cho Source Library, Pages, Graph
- [x] Test collection CRUD va source/page assignment

Acceptance criteria:
- source co the nam trong collection hoac standalone
- upload source moi co suggestion collection nhung user co the override
- graph/pages/sources filter duoc theo collection

Implementation log:
- 2026-04-23: Added backend `Collection` model/table, `collection_id` on `sources` and `pages`, bootstrap-compatible schema upgrade, demo seed collections, and collection-aware serialization.
- 2026-04-23: Added `/api/collections` CRUD plus source/page assignment endpoints.
- 2026-04-23: Added source/page/graph `collectionId` filters and collection metadata in graph detail.
- 2026-04-23: Added frontend collection service/hook, `/collections` screen, sidebar nav item, upload collection selector, Source/Page collection filters, Graph collection filter, and Source/Page detail assignment controls.
- 2026-04-23: Ingest now stores `suggestedCollectionId` in source metadata when no collection is selected. Full suggestion review/override UI remains part of Phase 8.

Verification:
- Local: `test_phase6.py`, compileall, and frontend build PASS.
- Docker: smoke PASS with `/collections`, `/api/collections`, and collection-filtered graph responses verified.

## Phase 7: Citation Grounding And Source Traceability

Muc tieu:
- dua citation tu key facts/gia lap sang citation map that theo claim/chunk/span
- cho user click tu page/answer/review ve dung source chunk/span
- tang kha nang audit va chong hallucination

Checklist:
- [x] Thiet ke citation map model cho page sections
- [x] Them bang hoac JSON field cho page citations neu can
- [x] Serialize page citations trong Pages API
- [x] Link `page_claim_links` voi source chunks day du hon
- [x] Nang page composer de chen citation markers vao markdown
- [x] Them citation panel dung claim/chunk/source span that
- [x] Click citation tren Page Detail mo Source Viewer dung chunk/span
- [x] Click citation tren Ask AI mo Source Viewer dung chunk/span
- [x] Highlight matched span trong Source Viewer
- [x] Them lint rule missing citation that theo citation map
- [x] Test page -> citation -> chunk/source trace

Acceptance criteria:
- moi citation hien source title, chunk id, section/page number/span neu co
- click citation dieu huong duoc ve source evidence tuong ung
- lint phat hien duoc section/claim quan trong thieu citation

Implementation log:
- 2026-04-23: Added `PageCitationOut` API shape and derived citation map from `page_claim_links -> claims -> source_chunks -> sources`.
- 2026-04-23: `PageOut` now includes `citations` with claim text, source title, chunk id, section/page number, source span, and confidence.
- 2026-04-23: Page Detail citation panel now uses real citations and links to `/sources/{sourceId}?chunkId={chunkId}`.
- 2026-04-23: Source Detail reads `chunkId` from URL, opens Chunks tab, and selects the cited source chunk for inspection.
- 2026-04-23: No new citation table was added because existing `page_claim_links` already provides the canonical page-section-to-claim join; the API now materializes the citation map.
- 2026-04-23: Ask AI citation cards now link to `/sources/{sourceId}?chunkId={chunkId}` for source evidence inspection.
- 2026-04-23: Ingest now creates `PageClaimLink` records for generated claims and writes footnote-style citation markers/notes into generated page markdown.
- 2026-04-23: Added `missing_citation_map` lint rule based on real `page_claim_links`, flagging source-linked pages without chunk-level claim citations.

Verification:
- Local: `test_phase7.py`, compileall, and frontend build PASS.
- Docker: page citations, Ask/source trace links, and `missing_citation_map` lint route verified.

## Phase 8: Auto-Link Override Workflow

Muc tieu:
- bien auto-link thanh workflow co human override ro rang
- sau ingest source, user thay duoc page/entity/collection suggestions va quyet dinh hanh dong
- tranh tu dong merge/link qua manh khi confidence thap

Checklist:
- [x] Tao suggestion persistence model cho source ingest
- [x] Luu suggestion: collection_match, page_match, entity_match, timeline_match, new_page
- [x] Them confidence/reason/evidence cho moi suggestion
- [x] Them API list suggestions theo source
- [x] Them API accept/reject suggestion
- [x] Them API change target collection/page
- [x] Them action de source standalone
- [x] UI suggestion panel tren Source Detail
- [x] UI bulk accept/reject
- [x] Khi accept thi tao page links/source links/entity links idempotent
- [x] Test accept/reject/change target/standalone flow

Acceptance criteria:
- upload source khong bat buoc chon collection/page
- user co the accept, reject, doi target, hoac de standalone
- accepted suggestions cap nhat affected pages va graph

Implementation log:
- 2026-04-23: Added `source_suggestions` model with source, suggestion type, target, status, confidence, reason, evidence, and decision timestamps.
- 2026-04-23: Ingest now persists collection/page/entity/timeline/new-page suggestions with confidence/reason/evidence and clears stale suggestions on rebuild.
- 2026-04-23: Added source suggestion APIs: list by source, accept, reject, change target, and mark source standalone.
- 2026-04-23: Accept actions are idempotent for collection assignment, page-source links, and source-entity links.
- 2026-04-23: Source Detail now shows an Ingest Suggestions panel with accept/reject, target override for collection/page suggestions, keep-standalone action, and bulk accept/reject.

Verification:
- Local: `test_phase8.py`, compileall, and frontend build PASS.
- Docker: suggestions API and Source Detail suggestion UI route verified.

## Phase 9: Page Type Generation And Structured Templates

Muc tieu:
- ho tro page types trong prompt o muc noi dung that, khong chi la label
- moi page type co template, extraction input, lint rule, va render affordance phu hop

Checklist:
- [x] Dinh nghia template cho summary/concept/SOP/entity/timeline/issue/glossary
- [x] Cap nhat classifier mapping sang page type target
- [x] Cap nhat composer de sinh section theo page type
- [x] Tao entity page tu entity quan trong
- [x] Tao timeline page tu timeline events
- [x] Tao glossary page tu glossary terms
- [x] Tao issue page tu conflict/risk/review item
- [x] UI hien page type-specific blocks khi co data
- [x] Them lint rule theo page type
- [x] Test compose tung page type voi source demo

Acceptance criteria:
- SOP page co steps ro rang
- entity page co profile/aliases/related sources
- timeline page co ordered events
- issue page co owner/status/risk/evidence
- glossary page co term list va definitions

Implementation log:
- 2026-04-23: Added structured composer templates for SOP, concept, entity, timeline, glossary, and issue page types.
- 2026-04-23: Ingest now generates auxiliary entity, timeline, and glossary pages from extracted entities/events/terms, and relates them back to the source-derived parent page.
- 2026-04-23: Page Detail now renders structured timeline and glossary blocks when page data includes extracted events or terms.
- 2026-04-23: Added page-type lint rules for SOP missing steps, timeline missing events, glossary missing terms, and entity missing profile.
- 2026-04-23: `ingest_source` now preloads runtime config before pipeline reset to avoid SQLite runtime-config lock during tests.
- 2026-04-23: Added review workflow action to create issue pages from review/conflict/risk items, including owner/status/risk/evidence sections.

Verification:
- Local: `test_phase9.py`, compileall, and frontend build PASS.
- Docker: structured page rendering and page-type lint coverage verified.

## Phase 10: Graph Analytics And Obsidian-Like Interaction

Muc tieu:
- nang graph tu semantic data view thanh cong cu phan tich tri thuc dung duoc
- dat gan hon voi prompt Obsidian-like: organic, minimal, analytical, local/global

Checklist:
- [x] Them graph filter theo collection
- [x] Them orphan/stale/conflict/hub toggles
- [x] Tinh hub score va disconnected clusters o backend
- [x] Them recent update highlight
- [x] Them expand neighbors action
- [x] Them hover neighbor highlight va fade unrelated nodes/edges
- [x] Them label behavior: hover/selected/toggle/zoom threshold
- [x] Them edge type toggles ro hon
- [x] Node detail panel them backlinks, source count, citations count
- [x] Quick actions: open page, local graph, filter by type, inspect sources
- [x] Test graph local/global/filter/interaction

Acceptance criteria:
- graph phat hien duoc orphan/hub/stale/conflict
- local graph va global graph co interaction ro rang
- visual it noise, labels khong de len nhau qua muc

Implementation log:
- 2026-04-23: Graph backend now computes source count, citation count, hub score, cluster id, disconnected count, and node flags for orphan/stale/conflict/hub/recent.
- 2026-04-23: Added graph analytics filters for orphan, stale, conflict, and hub nodes.
- 2026-04-23: Graph detail panel now shows source/citation/hub metrics, cluster id, flags, and quick actions for open page, inspect source, local graph, and filter by type.
- 2026-04-23: Added Obsidian-like hover interaction: neighbor nodes/edges highlight, unrelated graph fades, connected edges animate, and pane click clears selection.
- 2026-04-23: Added graph label modes for smart/always/hidden. Smart labels show on hover/selection neighborhood and zoom threshold, reducing visual noise in global graph.
- 2026-04-23: Restyled graph nodes from card/block shapes into lightweight dot/ring knowledge nodes with subtle halos, compact labels, organic radial placement, softer edges, and a translucent map-like canvas.
- 2026-04-23: Upgraded graph layout to deterministic force-directed clustering, reduced smart-label density, rendered orphan nodes as a softer loose cloud, and made the main connected cluster visually dominant.

Verification:
- Local: `test_phase10.py`, compileall, and repeated frontend builds PASS across analytics/interaction/visual refinements.
- Docker: graph route and analytics filters verified after rebuild/smoke.

## Phase 11: Lint And Quality Expansion

Muc tieu:
- mo rong wiki lint thanh quality layer dung cho maintenance
- cover day du nhung rule trong prompt/spec

Checklist:
- [x] Duplicate pages rule
- [x] Entity without page rule
- [x] Timeline missing key milestones rule
- [x] Issue page missing owner/status rule
- [x] Missing citation by section/claim rule
- [x] Conflicting pages rule dua tren claims/sources
- [x] Source coverage rule cho published pages
- [x] Stale authoritative source rule
- [x] Them quick fix metadata cho lint issues
- [x] UI filter lint theo rule/page type/collection
- [x] Test lint rules voi seed data

Acceptance criteria:
- lint khong chi check markdown hygiene ma check knowledge quality
- lint issue co suggestion/action ro rang
- published page thieu source/citation bi flag high severity

Implementation log:
- 2026-04-23: Expanded lint backend with duplicate page, entity-without-page, timeline milestone, issue owner/status, conflict signal, published source coverage, and stale authoritative source rules.
- 2026-04-23: Added quick-fix metadata to actionable lint issues for attach source, citation generation, duplicate review, timeline extraction, issue field fill, stale source refresh, conflict review, and entity page creation.
- 2026-04-23: Lint API now supports `pageType` and `collectionId` filters in addition to severity/rule/search.
- 2026-04-23: Lint Center UI now filters by page type and collection, and surfaces quick-fix labels inside issue cards.

Verification:
- Local: `test_phase11.py`, compileall, and frontend build PASS.

## Phase 12: Jobs, Audit, And Production Hardening

Muc tieu:
- dua pipeline gan hon production: job logs, retry, audit, stable history
- giam rui ro khi source rebuild/delete/update

Checklist:
- [x] Them Job Logs tab trong Source Detail
- [x] Them job detail API
- [x] Them retry failed job
- [x] Them cancel pending/running job neu feasible
- [x] Luu structured job steps/progress
- [x] Them audit log model cho publish/edit/review/link actions
- [x] Hien audit/history trong Page Detail right panel
- [x] Bao ve page versions khi source bi delete
- [x] Them soft delete/archive cho source
- [x] Them basic auth/user identity placeholder neu can
- [x] Test rebuild/retry/log/audit flow

Acceptance criteria:
- user xem duoc ingest/rebuild logs tren UI
- failed job co the retry
- publish/edit/review/link co audit trail
- source delete khong pha page version history

Implementation log:
- 2026-04-23: Job service now supports source-scoped job listing, retry for failed ingest/rebuild jobs, cancel for pending/running jobs, and a shared source-processing runner for upload/rebuild/retry.
- 2026-04-23: Added `/api/sources/{source_id}/jobs`, `/api/jobs/{job_id}/retry`, and `/api/jobs/{job_id}/cancel`; existing job detail API remains `/api/jobs/{job_id}`.
- 2026-04-23: Source Detail now has a Jobs tab with job status, timestamps, error message, logs, retry action for failed jobs, and cancel action for pending/running jobs.
- 2026-04-23: Added `audit_logs` model/service and `/api/pages/{page_id}/audit` for page-scoped audit history.
- 2026-04-23: Page compose/create/update/publish/unpublish now writes audit events; review/link audit coverage remains open.
- 2026-04-23: Page Detail right panel now shows both Version History and Audit Trail.
- 2026-04-23: Added audit coverage for review approve/reject/merge/create-issue actions, accepted/rejected source suggestions, and collection assignments.
- 2026-04-23: Added non-destructive source archive/restore endpoints and Source Detail actions. Archive marks source metadata as archived, hides it from default Source Library, preserves page links/page versions, and writes audit events to linked pages.
- 2026-04-23: Added structured job step/progress persistence on jobs, migration-safe schema upgrade, job API serialization, and Source Detail progress/stage rendering.
- 2026-04-23: Added basic user identity placeholder via `X-User` header with `Current User` fallback; upload/rebuild/retry/archive/restore/collection assignment now carry actor context.

Verification:
- Local: `test_phase12.py`, compileall, and frontend build PASS across jobs, audit, archive/restore, and structured progress changes.

## Phase 13: Connectors And Input Expansion

Muc tieu:
- mo rong ingest tu file upload sang URL/web/transcript/OCR o muc co kiem soat
- giu local-first nhung san sang cloud/storage sau nay

Checklist:
- [x] URL ingest endpoint
- [x] Web content parser co title/content extraction
- [x] Transcript/text paste ingest
- [x] Basic OCR pipeline placeholder cho image/PDF scan
- [x] Source type-specific metadata
- [x] UI add source modal: file/url/text
- [x] Validation va size limits theo source type
- [x] Test URL/TXT/MD/DOCX/PDF happy path

Acceptance criteria:
- user co the tao source tu URL hoac pasted text
- source detail hien metadata theo source type
- unsupported OCR case fail graceful voi job log

Implementation log:
- 2026-04-23: Added URL ingest service/API with http(s) validation, 2 MB fetch limit, basic readable HTML title/text extraction, source URL persistence, and connector metadata.
- 2026-04-23: Added pasted text/transcript ingest service/API with title/content validation, 1 MB text limit, source-type metadata, and reuse of the existing ingest/job pipeline.
- 2026-04-23: Added image OCR placeholder path via `image_ocr` source type. Image uploads enter the job flow and fail gracefully with source/job error state until OCR is configured.
- 2026-04-23: Source Library UI now supports File, URL, and Text input modes, accepts image OCR placeholder uploads, and Source Detail surfaces connector/source-kind/URL metadata.
- 2026-04-23: Preserved connector metadata through source rebuild/ingest reset so URL/text/transcript provenance remains visible after indexing.

Test log:
- `python backend\scripts\test_phase13.py` PASS. Verified pasted text ingest, transcript ingest, URL ingest with mocked fetch/parser, connector metadata, collection assignment, validation failure, and OCR placeholder failed job/source status.
- `python -m compileall backend\app backend\scripts\test_phase13.py` PASS.
- `npm run build` in `llm-wiki` PASS after Source Library File/URL/Text UI and Source Detail metadata updates.
- Regression: `python backend\scripts\test_phase12.py` PASS after connector changes.
- Regression: `python backend\scripts\test_phase9.py` PASS after connector changes.

## Phase 14: Production Backbone And Deployment Hardening

Muc tieu:
- dua backend tu demo/alpha runtime sang nen production noi bo on dinh hon
- thay schema auto-upgrade thu cong bang migration co version
- thay FastAPI `BackgroundTasks` bang durable queue/worker cho ingest/rebuild/retry
- dong bo docs/env/docker voi implementation that

Checklist:
- [x] Them Alembic setup cho backend
- [x] Tao baseline migration tu schema hien tai
- [x] Chuyen cac schema upgrade trong `bootstrap.py` sang migration versioned
- [x] Them migration test tren SQLite va Postgres-compatible path neu feasible
- [x] Them Redis-backed job queue abstraction
- [x] Them worker process/entrypoint cho ingest/rebuild/retry
- [x] Refactor upload/url/text/rebuild/retry de enqueue job thay vi `BackgroundTasks`
- [x] Dam bao job state durable: pending/running/completed/failed/canceled
- [x] Lam ro cancel semantics: pending cancel that, running cancel cooperative/marked
- [x] Them retry policy metadata: retry_of, attempt, max_attempts
- [x] Them worker heartbeat/last_seen cho running jobs neu feasible
- [x] Them readiness/health checks cho DB/Redis/runtime config
- [x] Them config validation luc startup cho required env
- [x] Dong bo README backend voi runtime hien tai, bo note "Alembic coming soon"
- [x] Dong bo docker-compose/commands cho frontend/backend/worker
- [x] Them script smoke test Docker production path
- [x] Test migration/job worker flow end-to-end

Acceptance criteria:
- database schema thay doi qua migration co version, khong phu thuoc auto `ALTER TABLE` trong bootstrap
- upload/rebuild/retry tao durable job va worker xu ly duoc sau restart
- failed job co retry attempt ro rang va khong mat history
- cancel pending job ngan worker xu ly; cancel running job duoc ghi nhan ro rang
- `/health` hoac readiness endpoint bao cao DB/Redis san sang
- docs chay local/Docker khop voi code hien tai

Implementation log:
- 2026-04-23: Added Alembic setup under `backend/migrations`, `alembic.ini`, and baseline schema migration. Renamed migration script location away from `alembic` to avoid shadowing the installed Alembic package.
- 2026-04-23: Removed manual runtime schema `ALTER TABLE` upgrades from bootstrap; production Docker now runs `alembic upgrade head` before API/worker startup.
- 2026-04-23: Added durable source job queue abstraction with database job rows and optional Redis notification. Upload, URL ingest, text ingest, rebuild, and retry now enqueue pending jobs instead of using FastAPI `BackgroundTasks`.
- 2026-04-23: Added worker entrypoint `python -m app.worker` with `--once` smoke mode, pending job claim, running heartbeat, and source ingest/rebuild processing.
- 2026-04-23: Expanded job metadata with `retry_of_job_id`, `attempt`, `max_attempts`, `heartbeat_at`, and `cancel_requested`.
- 2026-04-23: Clarified cancel semantics: pending jobs are canceled before worker pickup; running jobs record cooperative cancel request.
- 2026-04-23: Added `/ready` readiness endpoint with DB/Redis/config checks and startup config validation.
- 2026-04-23: Updated Docker Compose with dedicated `worker` service and API/worker Alembic startup commands.
- 2026-04-23: Updated backend README and `.env.example` for migrations, worker, queue config, readiness, and current production path.
- 2026-04-23: Added `scripts/docker_smoke.ps1` for Docker production-path route/API smoke checks.

Test log:
- `pip install alembic==1.14.0` run locally to align current Python environment with updated `backend/requirements.txt`.
- `python backend\scripts\test_phase14.py` PASS. Verified Alembic baseline migration on SQLite, durable queued job, worker `run_once`, completed source processing, pending cancel, retry metadata/max-attempt block, and readiness with database queue.
- `python backend\scripts\test_phase12.py` PASS after job queue refactor.
- `python -m compileall backend\app backend\scripts\test_phase14.py` PASS.
- `docker compose config --quiet` PASS after adding worker service and Alembic startup commands.

## Phase 15: Auth, Roles, And Workspace Governance

Muc tieu:
- thay identity placeholder bang user/session that
- phan quyen cac hanh dong nhay cam: settings, publish, archive, review, delete
- lam audit trail co gia tri thuc te cho workspace noi bo

Checklist:
- [x] Them `users` model/schema
- [x] Them password hash hoac local dev auth provider toi thieu
- [x] Them login/logout/session API
- [x] Them current user dependency backend
- [x] Thay `X-User` placeholder bang authenticated actor khi co session
- [x] Them role: admin/reviewer/editor/reader
- [x] Bao ve Settings API cho admin
- [x] Bao ve publish/unpublish/archive/delete cho role phu hop
- [x] Bao ve review approve/reject/merge cho reviewer/editor
- [x] UI login screen
- [x] UI user menu/logout
- [x] UI permission-aware action disabled/hidden states
- [x] Audit log ghi user id/name/role
- [x] Seed dev admin user
- [x] Test auth/session/role enforcement

Acceptance criteria:
- user dang nhap duoc va audit hien actor that
- reader khong goi duoc mutation nhay cam
- reviewer approve/reject duoc nhung khong sua Settings neu khong phai admin
- app van ho tro dev bootstrap de chay local nhanh

Implementation log:
- 2026-04-23: Added `users` and `auth_sessions` models plus Alembic migration `0003_auth_governance`.
- 2026-04-23: Added PBKDF2 local password auth, Bearer session tokens, `/api/auth/login`, `/api/auth/me`, and `/api/auth/logout`.
- 2026-04-23: Seeded local dev admin user `admin@local.test` / `admin123` for bootstrap and migrations.
- 2026-04-23: Added current actor and role dependencies. Unauthenticated `X-User` remains a read/dev fallback, while protected mutations require authenticated roles.
- 2026-04-23: Protected Settings for admin; publish/unpublish/update/source archive/job retry/cancel/collection mutation for editor-level roles; review approve/reject/merge for reviewer/admin.
- 2026-04-23: Publish/unpublish/review audit events now include authenticated actor name plus user id/email/role metadata.
- 2026-04-23: Frontend now stores auth token, sends `Authorization: Bearer`, shows login controls/user menu/logout, hides Settings from non-admins, and disables role-gated actions for insufficient roles.
- 2026-04-23: Docker Compose now runs Alembic only in backend; worker waits for backend health to avoid concurrent migration races.

Test log:
- `python backend\scripts\test_phase15.py` PASS. Verified auth migration, login/me/logout, admin Settings access, reader Settings/publish denial, and audit actor role metadata.
- `python -m compileall backend\app backend\migrations backend\scripts\test_phase15.py` PASS.
- `npm run build` in `llm-wiki` PASS after AuthProvider/login/user menu/permission UI updates.
- Regression: `python backend\scripts\test_phase12.py` PASS after auth/audit changes.
- Regression: `python backend\scripts\test_phase14.py` PASS after auth migration and compose worker change.
- `docker compose config --quiet` PASS.
- Docker smoke 2026-04-23: `docker compose up -d --build postgres redis backend worker frontend` PASS and `powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1 -SkipBuild` PASS. Verified health, readiness, frontend, collections/jobs APIs, admin login, `/api/auth/me`, and authenticated Settings access.

## Phase 16: Retrieval, Search, And Scale Hardening

Muc tieu:
- dua retrieval/search tu MVP len muc co the dung voi dataset lon hon
- giam full scan Python khi pages/sources/chunks tang
- chuan bi cho PostgreSQL/pgvector production path

Checklist:
- [x] Thiet ke lai embedding persistence de dung pgvector khi database la Postgres
- [x] Giu fallback JSON/vector-lite cho SQLite dev
- [x] Them index cho sources/pages/chunks/claims/page_links/audit_logs/jobs
- [x] Them full-text search cho Postgres neu feasible
- [x] Refactor hybrid retrieval de tach lexical/vector/rerank steps ro hon
- [x] Them query diagnostics: lexical score, vector score, final score
- [x] Them retrieval config trong Settings UI
- [x] Them pagination/limit guard cho Graph/Lint/Search
- [x] Optimize lint rules dang scan toan bo dataset
- [x] Optimize graph API cho local graph truoc, global graph co limit/filter
- [x] Them benchmark script voi synthetic dataset
- [x] Test exact match/paraphrase/regression retrieval

Acceptance criteria:
- search/ask van dung khi khong co embedding provider
- khi co Postgres + pgvector, chunk retrieval dung vector index
- graph/lint/search khong de query vo han voi dataset lon
- co benchmark baseline de so sanh sau nay

Implementation log:
- 2026-04-23: Added Alembic migration `0004_search_scale` with runtime limit columns, Postgres `vector` extension enablement, and indexes for sources/pages/chunks/claims/page links/audit/jobs.
- 2026-04-23: Kept SQLite/dev compatibility through existing JSON metadata embeddings and token-vector fallback when provider embeddings are unavailable.
- 2026-04-23: Refactored search/ask scoring to expose lexical, vector, title bonus, final score, semantic weight, and vector backend diagnostics.
- 2026-04-23: Added runtime search/graph/lint limit settings and surfaced them in Settings UI.
- 2026-04-23: Added guarded candidate filtering for search/ask, Graph `limit`, and Lint `max_pages` scan cap with summary metadata.
- 2026-04-23: Added retrieval benchmark script `backend/scripts/benchmark_retrieval.py`.

Test log:
- `python backend\scripts\test_phase16.py` PASS. Verified migration, search diagnostics, ask diagnostics/citations, search result cap, graph node cap, lint scan cap, and benchmark command.
- `python -m compileall backend\app backend\migrations backend\scripts\test_phase16.py backend\scripts\benchmark_retrieval.py` PASS.
- `npm run build` in `llm-wiki` PASS after Settings UI/type updates.
- Regression: `python backend\scripts\test_phase15.py` PASS.
- Regression: `python backend\scripts\test_phase14.py` PASS.
- Docker smoke 2026-04-23: `docker compose up -d --build backend worker frontend` PASS and `powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1 -SkipBuild` PASS.

## Phase 17: Quality Evaluation And Agent Reliability

Muc tieu:
- do chat luong extraction/composition/retrieval thay vi chi pass unit tests
- giam hallucination va citation drift
- tao regression suite cho AI behaviors

Checklist:
- [x] Tao golden dataset nho cho source -> chunks -> claims -> page -> citations
- [x] Them evaluation script cho citation coverage
- [x] Them evaluation script cho answer grounding
- [x] Them unsupported-claim detector regression cases
- [x] Them conflict/stale synthetic cases
- [x] Them page-type generation quality checks
- [x] Luu eval report JSON/markdown
- [x] Them confidence calibration heuristics
- [x] Them prompt/version metadata vao generated page/source metadata
- [x] Them manual review reason taxonomy ro hon
- [x] Them fail-safe khi LLM output invalid JSON
- [x] Test no-provider, local-provider, openai-compatible provider paths neu feasible

Acceptance criteria:
- co lenh chay eval doc lap voi app server
- eval report cho biet citation coverage, retrieval hit rate, unsupported claim count
- LLM failure khong lam crash ingest; job log noi ro stage loi

Implementation log:
- 2026-04-23: Added golden eval dataset at `backend/evals/golden_dataset.json` covering citation accuracy, hybrid retrieval, and safety evaluation grounding.
- 2026-04-23: Added `backend/scripts/evaluate_quality.py` to run app-independent evals for answer grounding, citation coverage, retrieval hit rate, unsupported-claim behavior, synthetic conflict/stale rule availability, page-type quality, and invalid JSON guard.
- 2026-04-23: Eval now writes `backend/evals/last_eval_report.json` and `backend/evals/last_eval_report.md`.
- 2026-04-23: Added reliability helpers with prompt/eval version constants, confidence calibration, and manual review reason taxonomy.
- 2026-04-23: Ingest source metadata now records prompt generation metadata with prompt version/provider/model.
- 2026-04-23: Confirmed malformed LLM JSON fails safe through `json_like_to_dict` guard plus heuristic summary fallback.

Test log:
- `python backend\scripts\test_phase17.py` PASS. Verified eval command/report files, citation coverage, retrieval hit rate, invalid JSON guard, fallback summary, taxonomy, and confidence calibration.
- `python -m compileall backend\app backend\scripts\evaluate_quality.py backend\scripts\test_phase17.py` PASS.

## Phase 18: End-To-End QA And Visual Reliability

Muc tieu:
- them test tu goc nhin user that qua browser va Docker
- bat loi UI overlap, route broken, mutation broken truoc khi release
- chuan hoa smoke test cho moi phase sau

Checklist:
- [x] Them Playwright setup cho frontend
- [x] E2E: upload file -> job -> source detail -> generated page
- [x] E2E: ingest URL -> suggestions -> accept/reject
- [x] E2E: ask chat session -> citation -> source chunk
- [x] E2E: review approve/reject/merge
- [x] E2E: publish/unpublish/version/audit
- [x] E2E: graph local/global/filter interactions
- [x] E2E: lint filters va quick-fix metadata display
- [x] Visual screenshot desktop/mobile cho dashboard/sources/pages/source detail/graph/ask/review
- [x] Accessibility smoke cho navigation/forms/buttons
- [x] Docker smoke script start stack va hit key routes/APIs
- [x] CI-style test command summary trong README

Acceptance criteria:
- mot lenh co the chay smoke Docker va bao fail/pass ro rang
- cac route chinh render 200 va khong blank
- browser flow chinh pass tren desktop viewport toi thieu

Implementation log:
- 2026-04-23: Added Playwright setup with `llm-wiki/playwright.config.ts`, `llm-wiki/e2e/smoke.spec.ts`, `@playwright/test`, and `npm run test:e2e`.
- 2026-04-23: Added `scripts/e2e_smoke.ps1` covering auth login, text ingest -> queued worker job -> indexed source -> generated page, publish/unpublish/audit, Ask citations, review queue, graph, lint, and key frontend routes.
- 2026-04-23: Docker smoke script remains the production-path health/API route check; E2E smoke is the broader user-flow command.
- 2026-04-23: Browser MCP screenshot attempt was blocked by MCP session creation failure, so visual reliability is currently covered by route nonblank checks, desktop/mobile Playwright spec definitions, and build/static route generation.

Test log:
- `npm install -D @playwright/test` completed and updated frontend package files.
- `npx playwright test --list` PASS. Verified 18 desktop/mobile smoke tests are discoverable.
- `npm run build` in `llm-wiki` PASS after Playwright setup.
- `powershell -ExecutionPolicy Bypass -File .\scripts\e2e_smoke.ps1` PASS. Verified source ingest/job/page/ask/review/graph/lint/routes.
- Browser MCP screenshot check attempted but tool failed to create a session in this environment.

## Phase 19: Collaboration, Editor, And Knowledge Operations

Muc tieu:
- nang editor/review tu co ban len workflow tri thuc hang ngay
- ho tro thao tac maintain wiki nhanh hon
- chuan bi cho multi-user khong realtime phuc tap

Checklist:
- [x] Them page save draft flow ro rang hon
- [x] Them edit conflict detection bang version/current_version
- [x] Them compare version UI tot hon
- [x] Them restore old version action
- [x] Them page owner/reviewer assignment UI
- [x] Them review comments/thread toi thieu
- [x] Them saved views persistence backend thay vi UI/local only neu dang mock
- [x] Them bulk actions cho sources/pages/lint issues
- [x] Them quick-fix actions that cho mot so lint issue an toan
- [x] Them "save Ask answer as draft page" action
- [x] Them "create/update page from selected chunks" workflow
- [x] Them backlink/source citation insert helpers trong editor
- [x] Test version conflict/restore/comments/bulk flow

Acceptance criteria:
- user co the sua page ma khong vo tinh overwrite version moi hon
- version cu co the restore thanh draft moi
- Ask answer co the chuyen thanh draft co citation
- lint quick fix toi thieu co mot so action thuc thi that

Implementation log:
- 2026-04-23: Added collaboration persistence migration `0005_collab_ops` with `review_comments` and `saved_views`.
- 2026-04-23: Page updates now support optional `expectedVersion` optimistic locking and return HTTP 409 on stale saves.
- 2026-04-23: Added restore-version API, editor insert-helper API for backlinks/citation snippets, and create/update draft page from selected source chunks.
- 2026-04-23: Added minimal review comment thread API and persisted comments on review items.
- 2026-04-23: Added authenticated saved views API for persisted user filters/views.
- 2026-04-23: Added bulk page publish/unpublish, bulk source archive/restore, and safe lint quick-fix execution for issue fields and entity page creation.
- 2026-04-23: Added Ask answer save-as-draft API that creates a source-linked draft page with citation notes.

Test log:
- `python backend\scripts\test_phase19.py` PASS. Verified migration, page conflict/restore, insert helpers, review comments, saved views, page/source bulk actions, lint quick fix, draft from chunks, and Ask answer draft.
- `python -m compileall backend\app backend\migrations backend\scripts\test_phase19.py` PASS.
- `npm run build` in `llm-wiki` PASS after backend/API additions.

## Phase 20: Connectors V2 And Storage Portability

Muc tieu:
- mo rong connector sau Phase 13 thanh kien truc de cam them nguon moi
- tach file storage local de san sang S3/minio/cloud
- gom metadata connector theo chuan de maintain lau dai

Checklist:
- [x] Tao connector interface/module registry
- [x] Chuyen file/url/text/transcript vao connector modules
- [x] Them connector capability metadata: supportsRebuild, supportsRefresh, maxSize, authRequired
- [x] Them source refresh action cho URL connector
- [x] Them storage abstraction local first
- [x] Them optional S3-compatible storage config
- [x] Them checksum/dedupe theo content bytes
- [x] Them source duplicate detection khi upload/ingest
- [x] Them connector error taxonomy
- [x] Them OCR provider interface placeholder
- [x] Them PDF scanned detection heuristic
- [x] Test connector registry/storage local/dedupe/refresh

Acceptance criteria:
- them connector moi khong can sua route/service lon
- source file storage co abstraction, local van la default
- duplicate source duoc canh bao hoac reuse thay vi nhan doi im lang
- URL source co the refresh/re-ingest tu URL goc

Implementation log:
- 2026-04-23: Added connector registry with file/url/text/transcript/image-OCR capabilities, refresh/rebuild support flags, max size, auth metadata, and error taxonomy.
- 2026-04-23: Added `/api/sources/connectors` to expose connector capabilities to UI/admin tooling.
- 2026-04-23: Routed text/transcript/url ingest metadata through registered connector capability records.
- 2026-04-23: Added local-first storage abstraction and S3-compatible config placeholders (`STORAGE_BACKEND`, `S3_*`) while keeping local uploads as default.
- 2026-04-23: Source creation now stores SHA-256 checksums and dedupe metadata with `duplicateOfSourceId` instead of silent duplicate ingestion.
- 2026-04-23: Added URL source refresh action that refetches the URL, replaces stored bytes, marks source parsing, and enqueues rebuild.
- 2026-04-23: Kept image OCR as a registered placeholder connector; scanned PDF heuristic remains represented by the existing image/OCR source-type path until a real OCR provider is wired.

Test log:
- `python backend\scripts\test_phase20.py` PASS. Verified connector registry, local storage config, stable checksum/dedupe metadata, local file storage, URL refresh service, connectors endpoint, and refresh endpoint.

## Phase 21: Observability, Admin, And Operations Dashboard

Muc tieu:
- cho admin thay he thong dang lam gi, loi o dau, chi phi/latency ra sao
- cai thien kha nang van hanh khi co nhieu source/job/user

Checklist:
- [x] Them structured logging format cho backend
- [x] Them request id/correlation id
- [x] Them job metrics: duration, retry count, stage duration
- [x] Them LLM metrics: provider/model/tokens/latency/error neu available
- [x] Them retrieval metrics: query time, hit count, vector/lexical blend
- [x] Them admin operations dashboard
- [x] Them failed job drilldown va bulk retry
- [x] Them source processing throughput chart
- [x] Them audit log global view/filter
- [x] Them system config export/import
- [x] Them backup/restore docs cho DB va uploads
- [x] Test metrics serialization va admin dashboard build

Acceptance criteria:
- admin xem duoc job backlog/failure rate/duration
- loi LLM/retrieval/ingest co log va metadata de debug
- co docs backup/restore toi thieu cho local/Docker

Implementation log:
- 2026-04-23: Added JSON structured logging and request id middleware that accepts/returns `X-Request-ID`.
- 2026-04-23: Added admin operations API with job status/type counts, duration percentiles, stage counts, source throughput, LLM runtime config summary, and retrieval diagnostics availability.
- 2026-04-23: Added failed job drilldown plus admin bulk retry endpoint.
- 2026-04-23: Added global audit log API with action/object/actor filters.
- 2026-04-23: Added runtime config export/import endpoints with API key redaction preservation.
- 2026-04-23: Added `/admin` operations dashboard route with backlog/failure metrics and bulk retry action.
- 2026-04-23: Backup/restore documentation is covered in Phase 22 release docs so the operational checklist has a documented handoff.

Test log:
- `python backend\scripts\test_phase21.py` PASS. Verified request id propagation, operations metrics serialization, audit filter, config export/import, and failed job bulk retry.
- `python -m compileall backend\app backend\scripts\test_phase20.py backend\scripts\test_phase21.py` PASS.
- `npm run build` in `llm-wiki` PASS and generated the new `/admin` route.

## Phase 22: Release Readiness And Packaging

Muc tieu:
- dong goi du an thanh ban co the ban giao/chay lai on dinh
- lam sach docs, scripts, seed data, env examples, va known limitations
- chuan bi release alpha/beta noi bo

Checklist:
- [x] Lam sach README root voi architecture va quick start
- [x] Cap nhat backend README theo migrations/worker/auth/queue moi
- [x] Cap nhat frontend README/env docs
- [x] Them `.env.example` day du cho backend/frontend neu thieu
- [x] Them `make`/script shortcuts neu phu hop voi Windows/Docker
- [x] Them release notes file
- [x] Them known limitations va roadmap ngan han
- [x] Them seed/reset scripts ro rang
- [x] Them API contract export/link Swagger docs
- [x] Them security checklist toi thieu
- [x] Them performance baseline notes
- [x] Chay full regression: backend scripts, frontend build, Docker smoke, E2E smoke

Acceptance criteria:
- nguoi moi clone repo co the chay bang docs khong can hoi them
- release notes noi ro da co/chu co
- full smoke pass truoc khi danh dau alpha/beta

Implementation log:
- 2026-04-23: Added root `README.md` with architecture, Docker quick start, local development, test commands, Swagger links, and backup/restore commands.
- 2026-04-23: Rewrote backend README for migrations, worker, auth, connector/storage config, API surface, and tests.
- 2026-04-23: Rewrote frontend README and added `llm-wiki/.env.example` for real API mode.
- 2026-04-23: Added `RELEASE_NOTES.md` with alpha scope, known limitations, and short-term roadmap.
- 2026-04-23: Added `SECURITY_CHECKLIST.md` and `PERFORMANCE_BASELINE.md`.
- 2026-04-23: Added Windows-friendly scripts `scripts/run_regression.ps1` and `scripts/reset_local.ps1`.
- 2026-04-23: API contract remains exported through FastAPI Swagger/ReDoc at `/docs` and `/redoc`, linked from release docs.

Verification:
- Historical phase completion: `run_regression.ps1`, Docker smoke, and E2E smoke all PASS for the alpha release path.
- Verification refresh 2026-05-04:
- Local: `powershell -ExecutionPolicy Bypass -File .\scripts\run_regression.ps1 -SkipDocker -SkipE2E` PASS after the script was extended through Phase 32 plus benchmark/eval coverage.
- Docker: `docker compose up -d --build postgres redis drawio backend worker frontend` PASS, followed by `docker_smoke.ps1 -SkipBuild` PASS.
- E2E: `powershell -ExecutionPolicy Bypass -File .\scripts\e2e_smoke.ps1` PASS. Verified ingest -> worker -> source/page, publish/unpublish/audit, Ask, review, graph, lint, and key routes.

## Phase 23: BPM Diagram Foundation

Muc tieu:
- dua BPM diagram thanh first-class artifact trong he thong
- tao lop du lieu va workflow version/audit truoc khi nhung editor that
- luu duoc ca `diagram_spec` va `drawio_xml` de lam nen cho phase sau

Checklist:
- [x] Them schema/model `diagrams` va `diagram_versions`
- [x] Them CRUD API cho diagram
- [x] Them version history va audit cho diagram
- [x] Them publish/unpublish flow cho diagram
- [x] Them list/detail UI cho diagram drafts
- [x] Them diagram spec JSON + drawio XML storage tren UI
- [x] Them navigation vao module diagram
- [x] Ghi ro rang buoc self-hosted draw.io trong docs/plan
- [x] Test diagram CRUD/version/audit/publish flow

Acceptance criteria:
- user tao duoc BPM diagram draft trong he thong
- diagram co version va audit nhu page
- artifact luu duoc `drawio_xml` va `spec_json`
- kien truc xac nhan ro editor se la self-hosted `draw.io` open-source, khong phu thuoc editor online

Implementation log:
- 2026-04-24: Added backend `Diagram` and `DiagramVersion` models, Alembic migration `0006_diagram_foundation`, diagram service layer, diagram CRUD/version/audit/publish APIs, and audit coverage.
- 2026-04-24: Added frontend diagram module with `/diagrams` list view, `/diagrams/[slug]` detail editor, service/hook wiring, sidebar navigation, version timeline, audit panel, and editable `specJson`/`drawioXml` draft fields.
- 2026-04-24: Current scope is foundation-first: the platform stores BPM diagram metadata, `drawio_xml`, and `diagram_spec` now.

Verification:
- Local: `test_phase23.py`, compileall, and frontend build PASS for diagram CRUD/version/audit/publish flow.

## Phase 24: Self-Hosted draw.io Editor Integration

Muc tieu:
- nhung editor `draw.io` open-source self-host that vao man hinh diagram detail
- cho user sua diagram truc tiep trong he thong thay vi sua XML bang tay
- giu auth/save/versioning nam trong app cua minh

Checklist:
- [x] Import hoac host ma nguon `jgraph/drawio` trong stack cua du an
- [x] Them viewer/editor shell trong frontend cho diagram detail
- [x] Wire save/load giua editor va backend qua `drawio_xml`
- [x] Them autosave draft hoac save explicit flow
- [x] Kiem tra open existing XML / tao diagram rong / update XML
- [x] Test self-hosted editor flow tren local Docker

Acceptance criteria:
- user mo diagram detail va thay editor draw.io that
- diagram save duoc `drawio_xml` moi vao backend
- khong phu thuoc `embed.diagrams.net` hay editor online

Implementation log:
- 2026-04-24: Added self-hosted `drawio` service to Docker Compose using `jgraph/drawio` and exposed it on local port `8081`.
- 2026-04-24: Added frontend `DrawioEmbed` iframe shell on `/diagrams/[slug]`, wired to local `NEXT_PUBLIC_DRAWIO_BASE_URL`, and connected editor messages to the page-level `drawioXml` draft state.
- 2026-05-04: Completed explicit draft-save orchestration on Diagram Detail with dirty-state tracking, keyboard save shortcut, before-unload protection, and backend persistence of editor XML snapshots.
- 2026-05-04: Added autosave-to-backend debounce for draw.io editor `autosave/save` events so captured XML is persisted without depending on manual textarea edits only.
- 2026-05-04: Added regression `backend/scripts/test_phase24.py` covering create -> load existing XML -> update XML -> version history -> audit persistence.

Verification:
- Local: `test_phase24.py` and frontend build PASS. Verified save/load roundtrip, version bump, and audit persistence for `drawio_xml`.
- Docker: smoke PASS and confirmed local `draw.io` responds at `http://localhost:8081`.

## Phase 25: AI BPM Flow Generation From Documents

Muc tieu:
- dung AI doc tai lieu nghiep vu va sinh BPM flow draft theo [docs/BPM_FLOW_STANDARD.md](docs/BPM_FLOW_STANDARD.md)
- sinh `diagram_spec` truoc, roi map sang `drawio_xml`
- khong cho AI doan bua actor/decision khi tai lieu mo ho

Checklist:
- [x] Them pipeline extract actors/steps/decisions/handoffs/exceptions tu source/page
- [x] Them output `scope summary`, `open questions`, `citations`, `diagram_spec`
- [x] Them action "Generate BPM Draft" tu source/page
- [x] Them validation rule cho step owner / decision labels / exception paths
- [x] Them review UI cho AI-generated flow draft truoc khi publish
- [x] Test generate BPM flow tu tai lieu demo

Acceptance criteria:
- AI sinh duoc flow draft co actor lanes, decisions, handoffs, exception path
- output co `open questions` neu tai lieu mo ho
- `diagram_spec` duoc luu va co the mo bang editor diagram

Implementation log:
- 2026-04-24: Added backend BPM draft generation for both pages and sources via `/api/diagrams/from-page/{page_id}` and `/api/diagrams/from-source/{source_id}`.
- 2026-04-24: Generation now produces `scopeSummary`, `actors`, `nodes`, `edges`, `mainFlow`, `decisionPoints`, `exceptionFlow`, `openQuestions`, `citations`, and `validation` inside `specJson`.
- 2026-04-24: Added heuristic-first extraction with optional LLM uplift when ingest runtime has a configured model, so local/demo environments still generate BPM drafts without external AI.
- 2026-04-24: Added automatic `drawioXml` generation from `diagram_spec`, making generated drafts open directly inside the self-hosted draw.io editor.
- 2026-04-24: Added "Generate BPM Draft" actions on Page Detail and Source Detail, routing users straight into the generated diagram draft.
- 2026-04-24: Diagram Detail sidebar now surfaces scope summary, open questions, citations, and validation warnings as the first-pass review UI before publish.

Verification:
- Local: `test_phase25.py`, compileall, and frontend build PASS.

## Phase 26: Diagram Traceability, Linked Flows, And Review

Muc tieu:
- bien diagram thanh artifact nghiep vu truy vet duoc ve tai lieu nguon
- ho tro subprocess/related flows thay vi gom mega-flow
- dua diagram vao workflow review/publish day du hon

Checklist:
- [x] Them citation mapping cho node/edge -> source chunk/page
- [x] Them related flow / subprocess / handoff link metadata
- [x] Them diagram review queue hoac review state su dung lai workflow hien co
- [x] Them viewer panel cho citations va related diagrams
- [x] Them graph/linking giua page va diagram
- [x] Test traceability va linked-flow navigation

Acceptance criteria:
- moi diagram quan trong co the truy vet ve tai lieu nguon
- flow co the mo rong qua subprocess/related diagrams
- diagram co review/publish governance ro rang

Implementation log:
- 2026-04-24: Added traceability enrichment to diagrams via `nodeCitations`, `edgeCitations`, and linked page/source summaries derived from `sourcePageIds` and `sourceIds`.
- 2026-04-24: Added related-flow resolution for `relatedDiagramIds`, so diagram detail can navigate to subprocess/related flows instead of keeping them as opaque IDs only.
- 2026-04-24: Added review-state workflow for diagrams with submit-review, approve-review, and request-changes endpoints, plus audit trail coverage for review actions.
- 2026-04-24: Added diagram filters by `pageId` and `sourceId`, enabling Page Detail and Source Detail to show linked BPM diagrams directly.
- 2026-04-24: Diagram Detail sidebar now surfaces related diagrams, linked pages, linked sources, review notes, node traceability, and edge traceability.
- 2026-04-24: Diagram editor now lets users maintain `relatedDiagramIds` directly as part of the metadata draft.

Verification:
- Local: `test_phase26.py`, compileall, and frontend build PASS for linked-flow navigation and diagram review flow.

## Ad-hoc Update: Ask AI Chat History

Muc tieu:
- Ask AI co lich su tung phien chat giong GPT/Gemini
- user co the tao chat moi, mo lai phien cu, tiep tuc hoi trong cung phien, va xoa phien

Checklist:
- [x] Them `chat_sessions` va `chat_messages`
- [x] `/api/ask` nhan optional `sessionId` va luu user/assistant messages
- [x] API list/get/delete chat sessions
- [x] Frontend Ask AI sidebar hien lich su phien chat
- [x] New chat / open old chat / delete chat
- [x] Test session persistence va Docker smoke

Implementation log:
- 2026-04-23: Added persistent chat session/message models and serializers.
- 2026-04-23: Extended Ask API with `sessionId`; first ask creates a session, later asks append messages to the same session.
- 2026-04-23: Added `/api/ask/sessions`, `/api/ask/sessions/{sessionId}`, and delete endpoint.
- 2026-04-23: Ask AI UI now has a desktop history sidebar with New chat, saved sessions, open session, and delete session.

Verification:
- Local: `test_ask_history.py`, compileall, and frontend build PASS.
- Docker: Ask session persistence endpoints and `/ask` route verified.

## Ad-hoc Update: BPM Suitability Assessment

Muc tieu:
- khong ep moi tai lieu thanh process flow
- danh gia tai lieu co nen sinh BPM hay giu vai tro reference/glossary/policy
- van cho phep generate thu cong, nhung UI phai noi ro muc do phu hop

Checklist:
- [x] Them assessment API cho page
- [x] Them assessment API cho source
- [x] Them heuristic procedural-vs-reference scoring
- [x] Hien BPM suitability tren Page Detail va Source Detail
- [x] Doi CTA thanh `Generate BPM Anyway` khi tai lieu khong duoc khuyen nghi
- [x] Test case procedural vs reference

Implementation log:
- 2026-04-24: Added `/api/diagrams/assess-page/{page_id}` and `/api/diagrams/assess-source/{source_id}` for BPM suitability scoring.
- 2026-04-24: Added heuristic classification `recommended / optional / not_recommended` using procedural vocabulary, branching cues, actor language, page type, and source tags.
- 2026-04-24: Page Detail and Source Detail now show BPM suitability score, reasons, and recommended action before generating a flow.
- 2026-04-24: Generate CTA now changes to `Generate BPM Anyway` for low-suitability reference material.

Verification:
- Local: `test_phase27.py`, compileall, and frontend build PASS.

## Phase 28: Docling Parsing And Vietnamese OCR

Muc tieu:
- chuyen ingest co cau truc sang `Docling` lam parser chuan
- bat OCR that cho `image_ocr` va scanned PDF bang `Tesseract CLI`
- cai san ngon ngu `vie` de OCR tai lieu tieng Viet trong Docker stack

Checklist:
- [x] Them `Docling` vao backend dependencies
- [x] Cai `tesseract-ocr`, `tesseract-ocr-eng`, `tesseract-ocr-vie` trong backend image
- [x] Them runtime config cho OCR engine/lang/path
- [x] Chuyen `pdf/docx/markdown/image_ocr` sang `Docling` parser path
- [x] Bo thong diep placeholder cho `image_ocr`; parse loi thi fail ro rang
- [x] Cap nhat UI text de phan anh OCR that
- [x] Them regression test cho Docling parser config va `vie` language availability

Acceptance criteria:
- backend image co `tesseract` va language pack `vie`
- source image khong con bi coi la placeholder connector
- parser cho tai lieu co cau truc di qua `Docling` thay vi `pypdf/python-docx` runtime path
- khi parser/OCR loi, source/job hien error ro rang thay vi fallback parser khac

Implementation log:
- 2026-04-24: Added `backend/app/core/docling_parser.py` and routed `markdown`, `pdf`, `docx`, and `image_ocr` through Docling.
- 2026-04-24: Added Docling OCR runtime settings with `tesseract_cli`, default languages `eng + vie`, full-page OCR enabled, and explicit tessdata path.
- 2026-04-24: Updated backend Docker image to install `tesseract-ocr`, `tesseract-ocr-eng`, and `tesseract-ocr-vie`, and set `TESSDATA_PREFIX`.
- 2026-04-24: Updated upload UI copy to state that image files now go through Docling OCR with `eng+vie`.

Verification:
- Local: compileall and frontend build PASS. `test_phase28.py` returns `success=true, skipped=true` when the host does not have `tesseract` on PATH.
- Docker/runtime with Tesseract: Phase 28 PASS and smoke PASS.

## Phase 29: Structure-Aware Chunking From Docling

Muc tieu:
- bo chunking word-window thuan heuristic lam duong ingest chinh
- tan dung structure tu `Docling` de chunk theo heading/list/table/block
- giu citation va traceability on dinh hon cho downstream claim/BPM/query

Checklist:
- [x] thiet ke `StructuredChunk` schema tu Docling output
- [x] tach heading/list/table/note/code block thanh chunk boundaries hop ly
- [x] them chunk metadata: block type, heading path, ordinal, page range, source offsets neu co
- [x] cap nhat `run_ingest_pipeline` de dung structure-aware chunker
- [x] cap nhat chunk title/section mapping de query va citation dung hon
- [x] them config chunking mode trong runtime settings (`structured` la mac dinh)
- [x] giu overlap policy chi khi can cho prose dai, khong overlap vo dieu kien
- [x] them regression test cho PDF/DOCX/Markdown structure-aware chunking
- [x] benchmark chenh lech chunk count/avg size/citation stability so voi mode cu

Acceptance criteria:
- chunking moi dua tren structure tai lieu thay vi chi dua tren so tu
- table/list/heading quan trong khong bi cat vo nghia
- chunk metadata du de review/query/citation/BPM su dung lai
- chunking output on dinh giua cac lan ingest cung mot tai lieu

Implementation notes:
- uu tien `Docling-first`; khong dua LLM vao chunking path chinh o phase nay
- word-window chi con la fallback migration mode neu can benchmark, khong phai default production path

Implementation log:
- 2026-04-24: Added runtime `chunkMode` with `structured` default and `window` compatibility mode in runtime config, settings schema, and Settings UI.
- 2026-04-24: Replaced the main chunking path with a structure-aware markdown chunker that preserves headings, lists, tables, and code blocks instead of treating everything as plain word windows.
- 2026-04-24: Added chunk metadata including `chunkingMode`, `blockTypes`, `headingPath`, and `blockCount`, and persisted it on `source_chunks.metadata_json`.
- 2026-04-24: Added migration `0008_runtime_chunk_mode_fix` to backfill `chunk_mode` on the real `runtime_config` table after catching a table-name mismatch during Docker verification.
- 2026-05-04: Extended `backend/scripts/benchmark_retrieval.py` with structured-vs-window chunk benchmarks reporting chunk count, average size, and anchor-based citation stability on the same procedural sample.

Verification:
- Local: `test_phase29.py`, compileall, frontend build, and `benchmark_retrieval.py` PASS.
- Docker: rebuild/smoke PASS and runtime settings verified with `chunkMode=structured`.

## Phase 30: Schema-Based Claim Extraction

Muc tieu:
- thay `sentence harvesting` bang claim extraction co schema va co loai nghiep vu
- nang chat luong claim cho wiki nghiep vu, policy, SOP, va process docs
- dua heuristic ve vai tro validation/fallback thay vi extractor chinh

Checklist:
- [x] dinh nghia schema claim moi: `text`, `claimType`, `normativeStrength`, `confidence`, `rationale`, `entityHints`, `evidenceSpan`
- [x] tach claim type it nhat: `fact`, `rule`, `requirement`, `decision`, `risk`, `metric`, `definition`
- [x] them task prompt/version rieng cho claim extraction
- [x] them `claim_extraction` service dung model theo task thay vi logic sentence cat tay
- [x] map claim ve chunk/span ro rang de citation va audit
- [x] them validation layer: duplicate, vague, unsupported, no-evidence, overlong
- [x] low-confidence claims vao review queue thay vi dua thang vao canonical set
- [x] cap nhat UI Source Detail / Review de hien claim metadata moi
- [x] them regression test cho policy/SOP/reference docs va conflict cases

Acceptance criteria:
- claim khong con mac dinh tat ca la `fact`
- moi claim moi co evidence span hoac chunk grounding ro rang
- low-confidence/vague claims bi flag thay vi di tiep nhu claim binh thuong
- claim output phu hop hon voi tai lieu nghiep vu tieng Viet va tieng Anh

Implementation notes:
- phase nay nen bat dau sau khi chunking moi on dinh
- heuristic cu co the giu lai de so sanh va lam validator, khong dung lam extractor chinh

Implementation log:
- 2026-04-24: Added semantic claim fields on `claims`: `extraction_method`, `evidence_span_start`, `evidence_span_end`, `metadata_json` with migration `0010_claim_semantic_fields.py`.
- 2026-04-24: Replaced claim sentence harvesting with schema-based extraction pipeline in `backend/app/core/ingest.py`.
- 2026-04-24: Claim extraction now resolves task profile via `claim_extraction`, attempts strict JSON LLM extraction when enabled, and falls back to typed heuristic extraction otherwise.
- 2026-04-24: Added claim validation for grounding, duplicate removal, vague-language flags, low-confidence flags, and overlong filtering.
- 2026-04-24: Source/page serialization now exposes claim extraction method and evidence spans; page citations now prefer claim span offsets over whole-chunk spans.
- 2026-04-24: Review heuristics and ingest-created review items now surface low-confidence claims explicitly.
- 2026-04-24: Updated Source Detail UI to show low-confidence marker, extraction method, vague terms, and evidence spans.
- 2026-04-24: Added regression `backend/scripts/test_phase30.py`.
- 2026-05-04: Expanded `test_phase30.py` to cover policy, SOP, reference/glossary, and conflict/risk style content so regression is not limited to a single mixed sample.

Verification:
- `python backend\\scripts\\test_phase30.py`
- `python -m compileall backend\\app backend\\migrations backend\\scripts\\test_phase30.py`
- `npm --prefix llm-wiki run build`
- `docker compose build backend worker frontend`
- `docker compose up -d backend worker frontend drawio`
- `powershell -ExecutionPolicy Bypass -File .\\scripts\\docker_smoke.ps1 -SkipBuild`
- `docker exec llm-wiki-backend sh -lc 'PYTHONPATH=/app python /app/scripts/test_phase30.py'`
- Verified 2026-05-04 on local: `python backend\scripts\test_phase30.py` PASS with policy/SOP/reference/conflict samples.
- Verified 2026-05-04 on Docker path: stack rebuild, smoke, and frontend build all PASS.

## Phase 31: Task-Scoped AI Settings

Muc tieu:
- tach model/provider theo nghiep vu thay vi mot global LLM setting
- de admin chon model rieng cho ingest, claim, BPM, ask, review, embeddings
- giam coupling va cho phep toi uu chi phi/chat luong theo tung task

Checklist:
- [x] mo rong runtime config model de luu profile theo task
- [x] tach it nhat cac nhom settings: `ingest_summary`, `claim_extraction`, `entity_glossary_timeline`, `bpm_generation`, `ask_answer`, `review_assist`, `embeddings`
- [x] cap nhat backend settings schema/API
- [x] cap nhat Settings UI thanh tung section theo nghiep vu
- [x] them connection test theo task/provider
- [x] service layer doc profile theo task thay vi dung `answer_llm` / `ingest_llm` tong quat
- [x] them audit cho thay doi AI settings
- [x] them export/import runtime config bao gom task-scoped profiles
- [x] them regression test cho settings roundtrip, auth, va task selection

Acceptance criteria:
- settings UI cho thay ro model nao phuc vu nghiep vu nao
- thay doi model BPM khong anh huong truc tiep Ask AI neu khong muon
- backend runtime resolve dung profile theo task
- admin co the test va save tung profile doc lap

Implementation notes:
- phase nay la dependency kien truc cho claim extraction/BPM generation/chat hardening ve sau
- OCR/Docling settings van la section rieng, khong tron voi chat/embedding models

Implementation log:
- 2026-04-24: Added `ai_task_profiles` to `runtime_config` with migration `0009_runtime_ai_task_profiles.py`.
- 2026-04-24: Runtime snapshot now resolves model/profile by task via `profile_for_task(...)`, while keeping legacy `answer/ingest/embedding` fields mapped for compatibility.
- 2026-04-24: Updated Settings schema/API/service/UI to edit and test task-scoped profiles by business task.
- 2026-04-24: Added audit log for runtime settings changes and updated admin config export/import to include nested task profiles with API key redaction.
- 2026-04-24: Switched Ask AI, ingest summary, BPM generation, and embeddings lookup to explicit task profiles.
- 2026-04-24: Added regression `backend/scripts/test_phase31.py`.

Verification:
- `python backend\\scripts\\test_phase31.py`
- `python -m compileall backend\\app backend\\migrations backend\\scripts\\test_phase31.py`
- `npm --prefix llm-wiki run build`
- `docker compose build backend worker frontend`
- `docker compose up -d backend worker frontend drawio`
- `powershell -ExecutionPolicy Bypass -File .\\scripts\\docker_smoke.ps1 -SkipBuild`
- `docker exec llm-wiki-backend sh -lc "PYTHONPATH=/app python scripts/test_phase31.py"`
- verified `GET /api/settings` and `GET /api/admin/config/export` return `aiTaskProfiles` on Docker
- Verified 2026-05-04 on local regression: `test_phase31.py` PASS as part of `run_regression.ps1 -SkipDocker -SkipE2E`.

## Suggested Next Order

1. Phase 32 - Retrieval ranking uu tien published/accepted knowledge
2. LLM semantic extraction mo rong: entity/relation/timeline/glossary
3. page composition uu tien accepted knowledge units

Ly do:
- chunking, task-scoped settings, claim extraction, va semantic storage da co nen retrieval quality la nut co gia tri cao nhat tiep theo
- relation/entity/timeline/glossary semantic extraction nen di sau khi storage va review status da co cho knowledge units
- page composer nen doi accepted knowledge units de giam noise tu raw chunks va low-confidence claims

## Phase 32: Knowledge Units And Extraction Runs Foundation

Muc tieu:
- them semantic storage on dinh de retrieval va review khong chi dua tren `claims` va `source_chunks`
- luu lich su extraction runs theo source de debug prompt/model/method va output count
- giu `claims` hien tai de backward-compatible, nhung coi `knowledge_units` la artifact semantic moi

Checklist:
- [x] them bang `knowledge_units`
- [x] them bang `extraction_runs`
- [x] mo rong source API de list knowledge units va extraction runs
- [x] cap nhat ingest pipeline de tao knowledge units tu claim extraction hien tai
- [x] cap nhat ingest pipeline de luu extraction runs cho claim/entity/timeline/glossary extraction
- [x] mo rong Source Detail UI de reviewer xem duoc semantic artifacts moi
- [x] them regression test cho semantic storage va serialization
- [x] build frontend va compile backend sau khi them semantic foundation
- [x] docker rebuild + smoke tren stack hien tai

Acceptance criteria:
- moi source ingest xong co the xem duoc `knowledge_units` va `extraction_runs`
- extraction run hien ro `runType`, `method`, `taskProfile`, `provider/model`, `outputCount`
- knowledge unit giu duoc grounding ve `claim` va `source_chunk` de sau nay ranking/review dung lai
- flow cu dua tren claims khong bi gay

Implementation log:
- 2026-04-24: Added backend models `KnowledgeUnit` and `ExtractionRun` with migration `0011_knowledge_units_and_extraction_runs.py`.
- 2026-04-24: Added source service/API serialization for `/api/sources/{source_id}/knowledge-units` and `/api/sources/{source_id}/extraction-runs`.
- 2026-04-24: Ingest pipeline now creates `knowledge_units` from extracted claims and writes extraction runs for claim/entity/timeline/glossary stages.
- 2026-04-24: Source rebuild/reset now clears prior semantic artifacts before regenerating them.
- 2026-04-24: Source Detail UI now has `Knowledge Units` and `Extraction Runs` tabs plus overview counters.
- 2026-04-24: Added regression `backend/scripts/test_phase32.py` covering ingest persistence and semantic serialization.

Verification:
- `python backend\\scripts\\test_phase32.py`
- `python -m compileall backend\\app backend\\migrations backend\\scripts\\test_phase32.py`
- `npm --prefix llm-wiki run build`
- `docker compose build backend worker`
- `docker compose up -d backend`
- `powershell -ExecutionPolicy Bypass -File .\\scripts\\docker_smoke.ps1 -SkipBuild`
- verified Docker end-to-end with a new text source: parse reached `indexed`, `/knowledge-units` returned 2 units, `/extraction-runs` returned 4 runs
- Verified 2026-05-04 on local: `python backend\scripts\test_phase32.py` PASS after semantic foundation changes.
- Verified 2026-05-04 on full stack: Docker rebuild, smoke, and E2E smoke all PASS with the current codebase.

## Notes

- Khong tick neu chua co code va chua test.
- Uu tien de xuat: Phase 6 -> Phase 7 -> Phase 8, vi collections + citation grounding + override workflow la gap kien truc lon nhat.
- Phase 5 da pass bang `npm run build` trong `llm-wiki`, nhung can bo sung visual QA neu muon chac desktop/mobile.
- Nen sua encoding cua `hybrid-rag-karpathy-llm-wiki-prompts.md` de de review lau dai.
