# AI Knowledge Workspace Gap Plan 2026

Date: 2026-05-12

Scope: evaluate the current `llm-wiki` codebase against the product target of an intelligent AI knowledge workspace: accurate answers, smart file storage, smart notes, and convenient evidence workflows.

## Executive Assessment

Current product maturity:

| Area | Current maturity | Target maturity | Gap severity |
| --- | ---: | ---: | --- |
| Ask AI answer quality | 3.7 / 5 | 4.7 / 5 | Medium |
| Citation and provenance precision | 3.5 / 5 | 4.7 / 5 | Medium |
| Storage and file lifecycle | 1.8 / 5 | 4.5 / 5 | High |
| Smart notes and annotations | 1.2 / 5 | 4.5 / 5 | High |
| Knowledge browsing workflow | 3.0 / 5 | 4.5 / 5 | Medium |
| Permissions and governance | 3.0 / 5 | 4.3 / 5 | Medium |
| Release readiness | 2.8 / 5 | 4.2 / 5 | High |

Bottom line:

- Ask AI is no longer a simple demo. It has scoped retrieval, notebook context, multimodal artifacts, citation selection, and regression scripts.
- The largest product gaps are not raw answer speed. They are durable storage, first-class notes, evidence-level workflows, and release hardening.
- To become a truly smart workspace, the next work should not add random UI pages. It should connect every source, answer, citation, page, review item, and user note around the same evidence model.

## Current State

### Ask AI

What exists:

- `backend/app/services/query.py` performs hybrid lexical/vector-style retrieval across source chunks, claims, knowledge units, page summaries, notebook notes, and artifacts.
- Ask responses include citations, answer strategy, diagnostics, and provenance-like payloads.
- Query filtering excludes low-quality source/page states and respects collection scope in several flows.
- Quality scripts exist: `backend/scripts/evaluate_quality.py`, `backend/scripts/benchmark_retrieval.py`, and compare reports.

Observed gaps:

- `query.py` is too large and combines retrieval, ranking, answer assembly, citation policy, conflict handling, and session persistence in one file.
- Citation selection has improved, but the target should be >= 90% precision on the local eval set before release.
- There is no explicit `EvidenceGrader` or `AnswerVerifier` service that can be tested independently.
- User feedback on answer quality is not persisted as training/evaluation signal.
- Ask API endpoints are not consistently permission-gated with the newer permission engine.

### Storage

What exists:

- `backend/app/core/storage.py` supports local file storage.
- Config already includes `STORAGE_BACKEND`, `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_REGION`, `S3_ACCESS_KEY_ID`, and `S3_SECRET_ACCESS_KEY`.
- `Source.file_path` and source metadata track stored upload path information.
- `SourceArtifactRecord` can persist image/table/OCR/structure artifact metadata.

Observed gaps:

- `STORAGE_BACKEND=s3` is configured but not implemented. The current code raises `StorageError` for non-local storage.
- There is no `StorageObject` database model for object key, bucket, checksum, byte size, content type, version, lifecycle status, or ownership.
- No MinIO service is wired in Docker Compose.
- No presigned URL flow exists for private file preview/download.
- No storage browser, object lifecycle policy, backup/restore verification, or orphan cleanup job exists.

### Smart Notes

What exists:

- Review comments exist through `ReviewComment`.
- Source ingest builds notebook-style metadata notes inside `Source.metadata_json.notebookContext`.
- Diagrams and skills carry review notes in JSON payloads.
- Ask can retrieve notebook notes generated from source content.

Observed gaps:

- There is no first-class `Note` model.
- Users cannot create a personal/team/workspace note anchored to a citation, source chunk, page section, artifact, graph node, or review item.
- Notes do not have privacy/scope, versioning, tags, backlinks, review status, or AI-suggested actions.
- Notes are not part of search/retrieval as user-owned evidence.
- There is no side panel or quick action to turn an Ask citation into a saved note.

### Permissions

What exists:

- `User`, `AuthSession`, `Department`, and `CollectionMembership` models exist.
- Login page and user management UI exist.
- `backend/app/services/permissions.py` defines a role-to-permission matrix and collection scope utilities.

Observed gaps:

- Some API routes still use role checks or no actor dependency instead of permission checks.
- `department_id` exists but department-level visibility is shallow.
- Role management UI should be treated as a permission catalog first, not a full custom RBAC engine yet.
- Collection scope currently allows global/null collection access broadly; that may be acceptable for shared public knowledge, but should be explicit in policy docs and UI.

### UX Workflow

What exists:

- Main product pages exist: dashboard, sources, pages, graph, Ask, review, skills, admin users/departments/roles.
- Source detail can inspect extracted artifacts and suggestions.
- Review can show evidence snippets and comments.

Observed gaps:

- The workflow is still page-centered rather than evidence-centered.
- Ask citations should open a consistent evidence side panel with actions: open source, open page, save note, request review, create page section.
- Source reader, page browser, graph, and review should share the same evidence card component.
- User management recently improved, but admin UX still needs stable table layout, drawer edits, and active menu correctness as release polish.

## Target State

The target is not "more pages". The target is a knowledge workspace where every important object is searchable, permission-aware, citeable, annotatable, and reviewable.

### Target 1: Smart Ask

Ask AI should:

- Answer only from indexed, permission-accessible, high-confidence evidence unless it clearly says evidence is missing.
- Use a dedicated retrieval pipeline: retrieve -> grade evidence -> assemble context -> generate answer -> verify answer -> select citations.
- Prefer minimal but sufficient citations.
- Show why each citation was used.
- Let the user save useful answer parts into notes or wiki pages in two clicks.

Release bar:

- Citation precision >= 90% on local eval cases.
- Unsupported claim rate = 0 on local eval cases.
- Text-only QA quality must not regress when multimodal retrieval is enabled.
- Every Ask answer should expose answer strategy, selected evidence, rejected evidence summary, and confidence.

### Target 2: Smart Storage

Storage should:

- Use local disk in dev and MinIO/S3-compatible object storage in Docker/prod.
- Persist every uploaded file and extracted artifact as a `StorageObject`.
- Track checksum, byte size, content type, object key, bucket, source linkage, artifact linkage, actor, and lifecycle state.
- Support private preview/download through signed URLs or backend streaming.
- Support backup/restore and orphan cleanup.

Release bar:

- New upload creates a source and a storage object in one transaction-safe flow.
- Object checksum dedupe prevents duplicate binary storage where possible.
- MinIO-backed upload/download smoke test passes in Docker.
- Source delete/archive does not accidentally delete audit-critical binary evidence.

### Target 3: Smart Notes

Notes should:

- Be a first-class resource, not only review comments or generated notebook metadata.
- Support scope: private, collection, workspace.
- Support anchors: source, source chunk, artifact, page, page section, Ask message, citation, graph entity, review item.
- Support tags, backlinks, versioning, and search.
- Support AI actions: summarize note, suggest linked pages, turn note into review item, turn note into page draft.

Release bar:

- User can create a note from an Ask citation in <= 2 clicks.
- Notes appear in search and Ask retrieval when permission allows.
- Notes have audit trail and collection/workspace scope.
- Notes can be promoted into page drafts or review items.

### Target 4: Evidence Workflow

The product should behave like this:

1. Upload or connect a source.
2. Ingest extracts text, chunks, claims, entities, images/tables/OCR, and storage objects.
3. Ask AI answers with grounded evidence.
4. User opens citation evidence side panel.
5. User saves a note, requests review, or creates/updates a wiki page.
6. Review queue validates changes with evidence.
7. Pages and graph reflect accepted knowledge.

Release bar:

- Ask citation -> source detail -> page -> graph -> review is one connected workflow.
- Same evidence card UI appears across Ask, source detail, pages, graph, and review.
- Every generated page or revision stores source/citation provenance.

## GAP Fix Plan

### P0: Storage Foundation

Objective: make file storage production-ready and MinIO-compatible.

Likely files:

- `docker-compose.yml`
- `backend/app/config.py`
- `backend/app/core/storage.py`
- `backend/app/models/records.py`
- `backend/migrations/0016_storage_objects.py`
- `backend/app/services/sources.py`
- `backend/app/api/sources.py`
- `llm-wiki/src/app/(main)/sources/[id]/page.tsx`

Implementation:

- Add MinIO service and bucket initialization to local Docker.
- Add `StorageObject` model and migration.
- Implement `local` and `s3`/MinIO adapters behind one storage interface.
- Store uploads and artifacts through the interface, not raw file paths.
- Add signed URL or backend download endpoint.
- Add orphan object cleanup script in dry-run mode first.

Verification:

- Unit test storage adapter local mode.
- Docker smoke: upload file -> object exists in MinIO -> source detail previews/downloads it.
- Regression: existing local uploads still work.

### P0: First-Class Notes

Objective: make notes a core knowledge primitive.

Likely files:

- `backend/app/models/records.py`
- `backend/migrations/0017_notes.py`
- `backend/app/api/notes.py`
- `backend/app/services/notes.py`
- `backend/app/services/query.py`
- `backend/app/services/permissions.py`
- `llm-wiki/src/lib/types/index.ts`
- `llm-wiki/src/services/real-notes.ts`
- `llm-wiki/src/hooks/use-notes.ts`
- `llm-wiki/src/components/evidence/*`
- `llm-wiki/src/app/(main)/ask/page.tsx`
- `llm-wiki/src/app/(main)/sources/[id]/page.tsx`

Implementation:

- Add `Note`, `NoteAnchor`, and `NoteVersion`.
- Add create/list/update/archive APIs with permission and scope checks.
- Add "Save note" action from Ask citation, source chunk, artifact, page section, and review item.
- Index notes into search/retrieval with note owner/scope filtering.
- Add notes side panel and notes tab on source/page detail.

Verification:

- Backend tests for note CRUD, anchors, scope filtering.
- UI smoke: create note from Ask citation, reopen source detail, see anchored note.
- Retrieval eval case: Ask can use a workspace-scoped note only when actor has permission.

### P1: Ask Intelligence Hardening

Objective: improve answer accuracy and make retrieval maintainable.

Likely files:

- `backend/app/services/query.py`
- `backend/app/services/retrieval.py`
- `backend/app/services/evidence_grader.py`
- `backend/app/services/answer_verifier.py`
- `backend/app/schemas/query.py`
- `backend/scripts/evaluate_quality.py`
- `backend/evals/*`
- `llm-wiki/src/app/(main)/ask/page.tsx`

Implementation:

- Split query service into retrieval, evidence grading, context assembly, answer generation, citation selection, and answer verification.
- Add evidence grade fields: relevance, specificity, authority, freshness, term coverage, contradiction risk.
- Add citation policy: max citations by intent, no weak citation unless answer depends on it, prefer direct source over summary when available.
- Persist answer feedback: helpful, wrong, missing source, bad citation.
- Extend eval cases for notes, artifacts, conflicting documents, archived sources, and permission scope.

Verification:

- `python backend/scripts/benchmark_retrieval.py`
- `python backend/scripts/evaluate_quality.py`
- Gate: citation precision >= 90%, unsupported claim rate = 0.

### P1: Evidence-Centered UX

Objective: make the product feel like one workspace instead of disconnected pages.

Likely files:

- `llm-wiki/src/components/evidence/*`
- `llm-wiki/src/app/(main)/ask/page.tsx`
- `llm-wiki/src/app/(main)/sources/[id]/page.tsx`
- `llm-wiki/src/app/(main)/pages/[slug]/page.tsx`
- `llm-wiki/src/app/(main)/graph/page.tsx`
- `llm-wiki/src/app/(main)/review/page.tsx`

Implementation:

- Create reusable `EvidenceCard`, `EvidenceDrawer`, and `EvidenceActions`.
- Add actions: open source, open page, save note, create review item, create page draft.
- Use the same evidence display in Ask, source detail, review, and page browsing.
- Keep sidebar and admin navigation stable; use drawers/modals for edits instead of long inline forms.

Verification:

- Frontend build.
- Manual smoke: Ask citation opens drawer, save note, open source, create review item.

### P1: Permission Completion

Objective: make auth/scope enforceable and understandable.

Likely files:

- `backend/app/api/*.py`
- `backend/app/services/permissions.py`
- `backend/app/services/auth.py`
- `llm-wiki/src/app/(main)/admin/*`
- `docs/permissions-and-scope.md`

Implementation:

- Replace remaining role-only dependencies with permission dependencies.
- Document collection/global/workspace/department policy clearly.
- Add route-level tests for reader/editor/reviewer/admin.
- Add UI gating for write actions.
- Keep department as metadata/filter first unless a real department-level security requirement is confirmed.

Verification:

- Backend permission tests.
- Manual smoke with reader, editor, reviewer, admin users.

### P2: Release Hardening

Objective: make the project safe to package and demo reliably.

Likely files:

- `scripts/*`
- `docs/QUALITY_RELEASE_CHECKLIST.md`
- `docs/upgrade-roadmap-2026.md`
- CI config if added later

Implementation:

- Clean untracked temporary folders before release packaging, especially `_tmp_arkon/`.
- Add one command for backend regression, frontend build, Docker smoke, and optional e2e.
- Add backup/restore smoke for Postgres plus MinIO.
- Add seed reset script for demo data.
- Add release notes template with known risks.

Verification:

- `powershell -ExecutionPolicy Bypass -File .\scripts\run_regression.ps1 -SkipDocker -SkipE2E`
- `powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1 -SkipBuild`
- Frontend production build.

## Recommended Implementation Order

1. Implement MinIO/S3 storage foundation.
2. Implement first-class notes and anchors.
3. Connect notes into Ask citations and source/page detail.
4. Refactor Ask retrieval into testable services and raise citation precision target to >= 90%.
5. Build shared evidence drawer/card workflow.
6. Complete permission coverage and route tests.
7. Run release hardening and clean packaging.

This order matters because smart notes and smarter Ask both need durable evidence storage. If Ask is optimized further before storage/notes exist, the work will likely be refactored again.

## Acceptance Metrics

The project can be considered release-candidate quality when these are true:

- Ask eval passes with citation precision >= 90%.
- Unsupported claim rate is 0 on local eval.
- MinIO-backed upload/download works in Docker.
- Every uploaded file has a persisted storage object.
- User can create an anchored note from an Ask citation in <= 2 clicks.
- Notes are searchable and permission-filtered.
- Reader/editor/reviewer/admin smoke tests pass.
- Docker smoke passes from a clean seed.
- No temporary competitor repo folders are included in release packaging.

## Immediate Next Sprint

Sprint goal: turn storage and notes from gaps into product foundations.

Deliverables:

- `StorageObject` model and MinIO adapter.
- Docker Compose MinIO service.
- Note/anchor/version models and APIs.
- Ask citation "Save note" action.
- Source detail notes tab.
- Backend tests for storage and notes permission.
- Updated quality eval with note and citation precision cases.

## Implementation Tracking Checklist

Use this section as the working checklist. Mark an item done only after code, migration/docs if needed, and relevant verification pass.

### P0.1 Storage Foundation

- [x] Audit current upload, source artifact, and download paths.
- [x] Define `StorageObject` schema: object key, bucket, backend, checksum, byte size, content type, owner, source id, artifact id, lifecycle state, timestamps.
- [x] Add migration for `storage_objects`.
- [x] Add SQLAlchemy model and serializer/schema.
- [x] Implement storage interface with `put`, `get`, `delete/mark`, `exists`, `signed_url` or streaming URL.
- [x] Keep current local storage behavior working.
- [x] Implement S3-compatible adapter for MinIO.
- [x] Add MinIO service to Docker Compose.
- [x] Add bucket initialization or startup check.
- [x] Update source upload to create `StorageObject`.
- [x] Update source artifact persistence to optionally create `StorageObject`.
- [x] Add backend download/preview endpoint.
- [x] Add source detail UI indicator for storage backend/object metadata.
- [x] Add dry-run orphan object cleanup script.
- [x] Update docs/env examples for local vs MinIO storage.

### P0.2 First-Class Notes

- [x] Audit existing review comments, notebook metadata, source suggestions, and page comments/notes.
- [x] Define `Note` schema: title, body, scope, visibility, owner, collection id, tags, status, timestamps.
- [x] Define `NoteAnchor` schema: target type, target id, citation id/message id, source id, chunk id, artifact id, page id, section key, review item id.
- [x] Define `NoteVersion` schema for edit history.
- [x] Add migration for notes, anchors, and versions.
- [x] Add backend notes service.
- [x] Add notes API: list, detail, create, update, archive, restore.
- [x] Add note scope filtering: private, collection, workspace.
- [x] Add note permission rules to permission matrix.
- [x] Add frontend note types/services/hooks.
- [x] Add note create drawer/modal.
- [x] Add "Save note" action from Ask citation.
- [x] Add "Save note" action from source detail/chunk/artifact.
- [x] Add notes tab or side panel on source/page detail.
- [x] Add note search indexing.
- [x] Add note retrieval candidates in Ask with permission filtering.
- [x] Add note-to-page-draft action.
- [x] Add note-to-review-item action.

### P1.1 Ask Intelligence Hardening

- [x] Extract retrieval candidate building out of `query.py`.
- [x] Extract evidence grading into a testable service.
- [x] Extract context assembly into a testable service.
- [x] Extract citation selection policy into a testable service.
- [x] Add answer verification step before final response.
- [x] Add evidence grade fields: relevance, specificity, authority, freshness, term coverage, contradiction risk.
- [x] Add per-citation reason shown to UI.
- [x] Add answer feedback persistence: helpful, wrong, missing source, bad citation.
- [x] Extend eval cases for notes.
- [x] Extend eval cases for storage artifacts.
- [x] Extend eval cases for conflicting documents.
- [x] Extend eval cases for scoped permission retrieval.
- [x] Raise eval gate for citation precision to `>= 90%`.
- [x] Ensure unsupported claim count remains `0`.

### P1.2 Evidence-Centered UX

- [x] Define shared `EvidenceCard`.
- [x] Define shared `EvidenceDrawer`.
- [x] Define shared `EvidenceActions`.
- [x] Replace Ask citation details with shared evidence components.
- [x] Replace source detail evidence snippets with shared evidence components.
- [x] Add page evidence/backlink drawer.
- [x] Add graph node evidence actions.
- [x] Add review evidence drawer/actions.
- [x] Add actions: open source, open page, ask scoped, save note, create review item, create page draft.
- [x] Keep sidebar/menu active state correct on admin child routes.
- [x] Keep admin user/department/role pages as separate pages with table + drawer editing, not giant inline forms.

### P1.3 Permission Completion

- [x] Audit all backend routes for auth dependency.
- [x] Replace remaining role-only route checks with permission checks where appropriate.
- [x] Add permission tests for reader.
- [x] Add permission tests for editor.
- [x] Add permission tests for reviewer.
- [x] Add permission tests for admin.
- [x] Document global, collection, workspace, and department policy.
- [x] Add UI gating for create/edit/delete actions.
- [x] Add denied-state UI instead of broken buttons.
- [x] Confirm Ask/search cannot leak restricted collection evidence.

### P2 Release Hardening

- [x] Remove or exclude `_tmp_arkon/` from release packaging.
- [x] Curate git status and separate intentional changes from temporary files.
- [x] Add one-command local regression script.
- [x] Add one-command Docker smoke script or improve current one.
- [x] Add clean seed/reset script for demo data.
- [x] Add Postgres backup/restore smoke.
- [x] Add MinIO backup/restore smoke.
- [x] Add release notes template.
- [x] Add production env checklist: JWT secret, CORS, upload limits, retention, audit export, backup schedule.
- [x] Run full release candidate verification from a clean Docker stack.

## Test Tracking Checklist

Use this section to decide whether a phase is truly done. Do not mark a phase complete if its required tests are not run or explicitly waived with risk noted.

### Backend Unit/Service Tests

- [x] Storage local adapter can write/read metadata.
- [x] Storage MinIO adapter can write/read metadata.
- [x] Storage checksum dedupe works or explicitly logs duplicate objects.
- [x] Source upload creates `Source` and `StorageObject`.
- [x] Artifact persistence creates/links storage object when binary artifact exists.
- [x] Note CRUD works.
- [x] Note version history works.
- [x] Note anchor creation works for Ask citation.
- [x] Note anchor creation works for source chunk.
- [x] Note anchor creation works for artifact.
- [x] Note anchor creation works for page section.
- [x] Note scope filtering works for private notes.
- [x] Note scope filtering works for collection notes.
- [x] Note scope filtering works for workspace notes.
- [x] Permission denied cases return 403, not empty misleading success.
- [x] Ask/search cannot retrieve restricted notes or sources.

### Ask AI Quality Tests

- [x] `python backend/scripts/benchmark_retrieval.py` passes.
- [x] `python backend/scripts/evaluate_quality.py` passes.
- [x] Citation precision is `>= 90%`.
- [x] Unsupported claim count is `0`.
- [x] Text-only QA does not regress.
- [x] Multimodal artifact case passes.
- [x] Note retrieval case passes.
- [x] Conflict/authority case passes.
- [x] Archived/deprecated source exclusion case passes.
- [x] Scoped collection retrieval case passes.
- [x] Feedback logging does not alter answer quality.

### API Smoke Tests

- [x] `POST /api/auth/login`.
- [x] `GET /api/auth/me`.
- [x] `GET /api/collections`.
- [x] `POST /api/sources/upload`.
- [x] `GET /api/sources/{id}`.
- [x] `GET /api/sources/{id}/artifacts`.
- [x] `GET /api/storage/objects/{id}` or equivalent download/preview endpoint.
- [x] `POST /api/ask`.
- [x] `POST /api/notes`.
- [x] `GET /api/notes`.
- [x] `PATCH /api/notes/{id}`.
- [x] `DELETE` or archive note endpoint.
- [x] `POST /api/review-items`.
- [x] Admin users/departments/roles endpoints.

### Frontend Build And UI Smoke

- [x] `npm --prefix llm-wiki run build` passes.
- [x] Login page works before entering app.
- [x] Sidebar remains visible and active state is correct.
- [x] Users page uses table/list layout and drawer/modal edit.
- [x] Departments page works.
- [x] Roles page works.
- [x] Upload source works.
- [x] Source detail shows storage/object metadata.
- [x] Source detail shows artifacts.
- [x] Ask answer shows citations.
- [x] Ask citation opens evidence drawer.
- [x] Ask answer shows visible evidence verification status.
- [x] Ask citation can save note in <= 2 clicks.
- [x] Saved note appears on source/page detail.
- [x] Saved note appears in search/Ask when permission allows.
- [x] Review queue can open evidence and note context.
- [x] Graph/page navigation from evidence works.

### Docker And Release Tests

- [x] `docker compose up -d --build` succeeds from stopped stack.
- [x] Backend health/readiness returns 200.
- [x] Frontend returns 200.
- [x] Postgres starts without port conflict.
- [x] Redis starts.
- [x] MinIO starts.
- [x] MinIO bucket exists.
- [x] Upload file through UI/API stores object in MinIO.
- [x] Download/preview file works from Docker stack.
- [x] Worker processes ingest job.
- [x] Docker smoke script passes.
- [x] Backup/restore smoke passes for Postgres.
- [x] Backup/restore smoke passes for MinIO.
- [x] Clean seed reset dry-run works.

### Manual Acceptance Tests

- [x] Reader can view allowed knowledge but cannot create/edit restricted objects.
- [x] Editor can upload sources, create notes, and draft pages.
- [x] Reviewer can review evidence and approve/request changes.
- [x] Admin can create user, assign department, assign role, and assign collection access.
- [x] Ask answer includes enough evidence but not noisy extra citations.
- [x] User can go from Ask answer to citation to source to note to review/page without losing context.
- [x] Product can be demoed from a fresh Docker stack without manual DB patching.
