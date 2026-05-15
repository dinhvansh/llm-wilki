# Codebase Status - 2026-05-15

Scope: direct codebase read-through of the current repository state on `2026-05-15`, including backend, frontend, docs/plans, local runtime stack, and the in-progress OpenFlowKit migration.

## Executive Summary

The project is no longer a prototype-level CRUD app. It is a fairly large internal knowledge workspace with:

- FastAPI backend
- Next.js frontend
- worker/job pipeline
- Postgres + pgvector
- Redis
- MinIO-backed object storage
- embedded OpenFlowKit diagram editor

The codebase already contains meaningful product depth:

- source ingest and artifact extraction
- grounded Ask AI with diagnostics and citations
- page generation and review workflows
- permission and collection scoping
- first-class notes
- evidence-centered UX surfaces
- skill package registry

The repo is also in an active transition:

- the old draw.io-based diagram flow is being replaced by OpenFlowKit
- runtime AI settings/secrets are being hardened
- several docs and scripts still reflect the pre-migration draw.io world

Verdict:

- product maturity: solid local/internal demo quality
- architecture maturity: mixed; several strong foundations, but still some large hotspot files
- release hygiene: not clean yet
- current branch state: actively in-flight, not a clean release snapshot

## Repo Shape

Top-level modules:

- `backend/`: FastAPI API, worker, migrations, services, eval scripts
- `llm-wiki/`: Next.js 15 frontend app
- `openflowkit/`: self-hosted diagram editor runtime
- `docs/`: roadmap, release, workflow, migration notes
- `scripts/`: smoke, regression, reset, backup/restore

The repo is effectively a monorepo, but without one unified build/test orchestrator at the root. Each major app still carries its own runtime and testing conventions.

## Current Product Architecture

### Backend

Observed from [backend/app/main.py](/d:/AI-native wiki platform/backend/app/main.py:1):

- FastAPI app
- CORS enabled from config
- startup bootstrap seeds/init DB
- static upload mount at `/uploads`
- API routers for:
  - auth
  - dashboard
  - jobs
  - admin
  - collections
  - diagrams
  - sources
  - notes
  - pages
  - review
  - saved views
  - query
  - graph
  - lint
  - settings
  - skills

### Frontend

Observed from [llm-wiki/src/app/layout.tsx](/d:/AI-native wiki platform/llm-wiki/src/app/layout.tsx:1) and [llm-wiki/src/app/(main)/layout.tsx](/d:/AI-native wiki platform/llm-wiki/src/app/(main)/layout.tsx:1):

- App Router Next.js app
- global `AuthProvider` + `QueryProvider`
- auth-guarded main shell
- persistent sidebar and top bar
- workspace-style IA rather than marketing/landing structure

Primary routes present in code:

- `/`
- `/login`
- `/collections`
- `/sources`
- `/pages`
- `/ask`
- `/graph`
- `/review`
- `/lint`
- `/settings`
- `/skills`
- `/entities`
- `/timeline`
- `/glossary`
- `/diagrams`
- `/diagram-flow/[slug]`
- `/admin/*`

### Diagram Runtime

Observed from `docker-compose.yml`, [llm-wiki/src/components/diagram/openflowkit-embed.tsx](/d:/AI-native wiki platform/llm-wiki/src/components/diagram/openflowkit-embed.tsx:1), and [docs/openflowkit-migration-blueprint.md](/d:/AI-native wiki platform/docs/openflowkit-migration-blueprint.md:1):

- OpenFlowKit runs as a separate app
- frontend embeds it by iframe
- save/load uses `postMessage`
- backend remains source of truth for durable diagram state
- OpenFlowKit browser storage is editor runtime state only

This is the biggest active architectural migration in the repo right now.

## Domain Model Status

Observed from [backend/app/models/records.py](/d:/AI-native wiki platform/backend/app/models/records.py:1):

Core entities already exist:

- `Source`
- `SourceChunk`
- `SourceArtifactRecord`
- `StorageObject`
- `Collection`
- `Department`
- `Note`
- `NoteAnchor`
- `NoteVersion`
- `Entity`
- `Claim`
- `KnowledgeUnit`
- `ExtractionRun`
- page/diagram/review/auth/session related models further down the file

This is not a thin schema anymore. The backend has grown into a real knowledge-domain model with evidence, extraction, governance, and review concepts.

## What Is Already Implemented

Based on docs plus direct code inspection, the implemented surface is broadly consistent with the repository claims:

### 1. Knowledge ingest and evidence extraction

- uploads, URL ingest, text ingest
- chunking
- OCR and multimodal artifact persistence
- source artifacts and notebook/structured metadata

### 2. Ask AI workflow

- retrieval orchestration
- citation payloads
- answer diagnostics
- feedback endpoint
- evidence grading and answer verification surfaces

### 3. Wiki and review

- pages
- revisions
- backlinks/evidence navigation
- review queue and comments
- note to page/review actions

### 4. Access control

- login/logout/me
- users/departments/roles admin UX
- collection membership model
- permission-based route gating across most business routes

### 5. Storage

- local storage adapter
- S3-compatible path using MinIO
- `StorageObject` persistence
- backend download/preview support

### 6. Diagram system

- diagram list/detail flows
- backend `flowDocument` handling
- OpenFlowKit embed
- BPM skill package for AI-generated flows

## Code Hotspots

These files are carrying a lot of responsibility and are likely maintainability hotspots:

Backend:

- `backend/app/services/query.py`: about `2503` lines
- `backend/app/services/sources.py`: about `2150` lines
- `backend/app/services/diagrams.py`: about `1439` lines
- `backend/app/services/pages.py`: about `976` lines

Frontend:

- `llm-wiki/src/app/(main)/sources/[id]/page.tsx`: about `1524` lines
- `llm-wiki/src/app/(main)/ask/page.tsx`: about `941` lines
- `llm-wiki/src/app/(main)/pages/[slug]/page.tsx`: about `913` lines
- `llm-wiki/src/app/(main)/graph/page.tsx`: about `832` lines

Implication:

- the system has already been refactored some amount
- but several critical flows still remain page-heavy or service-heavy
- the main risk is not lack of features; it is concentration of behavior in large files

## Things That Look Strong

### 1. Product direction is coherent

The repo is not wandering feature-by-feature. The main loop is consistent:

`source -> evidence -> ask -> note/review/page -> graph/knowledge reuse`

That coherence is visible in both docs and code.

### 2. Permission model is beyond simple role checks

Observed from [backend/app/services/permissions.py](/d:/AI-native wiki platform/backend/app/services/permissions.py:1):

- role-to-permission matrix exists
- collection scope exists
- collection filtering helpers exist
- frontend navigation consumes permissions

That is a meaningful step above a flat admin/user gate.

### 3. Storage foundation is real

Observed from [backend/app/core/storage.py](/d:/AI-native wiki platform/backend/app/core/storage.py:1):

- `local` and `s3`/MinIO flows exist
- object metadata is persisted
- backend can stream/read stored content

This is substantial product infrastructure, not placeholder code.

### 4. Notes are first-class

Observed from [backend/app/services/notes.py](/d:/AI-native wiki platform/backend/app/services/notes.py:1):

- note CRUD
- note versions
- note anchors
- note scope
- note promotion flows

That makes the workspace more than just generated pages and search.

### 5. OpenFlowKit migration has a concrete path

The OpenFlow migration is not hand-wavy:

- dedicated blueprint exists
- backend serializes `flowDocument`
- frontend has separate editor route
- skill package contract exists for BPM output

## Current Weaknesses and Risks

### 1. Diagram migration is incomplete at repo level

The active code is moving to OpenFlowKit, and legacy draw.io residue still exists in historical docs, migrations, and compatibility paths:

- docs still reference draw.io as an earlier runtime
- migrations and old test fixtures still mention `drawio_xml`
- migrations and legacy columns still contain `drawio_xml`

Concrete example:

- the compatibility/migration docs still discuss `drawioXml` because old records and earlier editor flows existed before the OpenFlowKit cutover
The repo-facing automation drift has been cleaned, but the documentation tail from the old engine still needs consolidation.

### 2. Automation is script-heavy and fragmented

Observed from [scripts/run_regression.ps1](/d:/AI-native wiki platform/scripts/run_regression.ps1:1):

- test flow is a long chain of numbered scripts
- there is no clean single test taxonomy like unit/integration/contract/e2e
- some validation is documented in notes rather than enforced by CI

That works for a solo or tight internal loop, but it does not scale cleanly.

### 3. No root CI workflow was found

Direct repo inspection did not reveal a root `.github/workflows/*` pipeline for this monorepo.

Implication:

- release confidence depends on manual script discipline
- regressions are more likely to slip when the repo stays dirty or multiple tracks move together

### 4. Several core surfaces are still too large

The big files listed above indicate:

- backend service orchestration is still centralized in a few modules
- frontend page containers still render and orchestrate too much

This is the biggest maintainability risk after feature breadth.

### 5. Auth/session approach is practical but not hardened

Observed from [llm-wiki/src/providers/auth-provider.tsx](/d:/AI-native wiki platform/llm-wiki/src/providers/auth-provider.tsx:1) and [llm-wiki/src/services/api-client.ts](/d:/AI-native wiki platform/llm-wiki/src/services/api-client.ts:1):

- auth token is stored in `localStorage`
- frontend also keeps `X-User` compatibility header

That is workable for internal/local deployment, but it is not where a stricter production security posture would stop.

### 6. Scope defaults are intentionally permissive

Observed from [backend/app/services/permissions.py](/d:/AI-native wiki platform/backend/app/services/permissions.py:1):

- if a non-admin user has no collection memberships, scope falls back to `mode="all"`

That may be deliberate for shared-workspace defaults, but it is permissive and should remain explicitly documented as policy.

### 7. Documentation hygiene is uneven

Observed directly:

- some docs/readmes show encoding damage or mojibake
- multiple planning docs still refer to old architecture/runtime assumptions
- release notes and plans are numerous and partially overlapping

This does not block local work, but it increases cognitive load.

## OpenFlowKit Migration Status

Current status based on code and git history:

- recent commits are explicitly diagram-migration related:
  - `d7e7fb6 feat: complete openflow diagram scope`
  - `48c4c4d feat: replace diagram editor with openflow engine`
  - `e2a7f2c docs: plan openflowkit diagram migration`
- current worktree still has uncommitted changes across backend, frontend, docs, env examples, and docker compose
- route `diagram-flow/[slug]` exists and is already wired to the new editor flow
- `backend/app/services/diagrams.py` now uses `flowDocument` actively

Assessment:

- migration is well underway
- migration is not fully normalized across scripts/docs/tests
- repo-wide cleanup after the cutover is still needed

## Frontend Assessment

Observed characteristics:

- the app shell is coherent and permission-aware
- navigation is grouped by workflow, not only feature type
- there is a real attempt to unify evidence surfaces
- the frontend leans on React Query and service wrappers cleanly

Main concerns:

- detail pages are still too large
- some state orchestration lives directly in page files
- admin and evidence flows likely need further component extraction if the product keeps growing

## Backend Assessment

Observed characteristics:

- the backend is the real product core
- service layer is broad and capable
- domain concepts are richer than a typical thin API
- scripts for eval and regression are substantial

Main concerns:

- some services are oversized
- a lot of product logic lives in Python service modules without a stronger internal modular boundary
- the codebase is powerful, but it is nearing the point where more features without further splitting will slow change velocity

## OpenFlowKit Assessment

Observed from [openflowkit/ARCHITECTURE.md](/d:/AI-native wiki platform/openflowkit/ARCHITECTURE.md:1) and [openflowkit/package.json](/d:/AI-native wiki platform/openflowkit/package.json:1):

- OpenFlowKit itself is a serious standalone codebase
- it has React 19, Vite, Zustand, ELK, Mermaid, collaboration, export, tests, benchmarks
- this is not a thin embedded widget; it is a full product in its own right

Implication:

- embedding it gives the wiki a stronger diagram foundation
- but it also adds another sizable subsystem to maintain and integrate

## Runtime Stack Status

Observed from [docker-compose.yml](/d:/AI-native wiki platform/docker-compose.yml:1):

The intended local stack is:

- frontend on `3100`
- backend on `18000`
- OpenFlowKit on `3045`
- signaling server on `31234`
- Postgres on `55432`
- Redis on `56379`
- MinIO on `19000/19001`

This is a serious local environment, not a toy dev setup.

## Release Readiness Assessment

As of `2026-05-15`:

- local/internal demo readiness: high
- repo consistency readiness: medium-low
- clean release packaging readiness: medium-low
- production-hardening readiness: not yet

Why not ready-clean yet:

- active dirty worktree
- historical documentation overlap around draw.io vs OpenFlowKit
- no root CI enforcement visible
- large hotspot files remain
- auth/storage/security posture is pragmatic rather than fully hardened

## Recommended Next Steps

### Priority 1

Finish repo-wide OpenFlow cutover:

- remove or explicitly quarantine legacy draw.io assumptions in docs
- decide which draw.io compatibility pieces remain intentionally supported

### Priority 2

Reduce hotspot size in core files:

- split `query.py` further by retrieval/planning/answer assembly/citation serialization
- split `sources.py` by ingest/storage/artifact/rebuild concerns
- split large frontend detail pages into screen model + section components

### Priority 3

Normalize automation:

- add a root CI workflow
- define smaller named test suites instead of only numbered phase scripts
- keep Docker smoke aligned with actual compose services

### Priority 4

Tighten operational/security posture:

- revisit token storage approach
- make scope fallback policy explicit
- keep secrets/runtime config handling consistent after the current changes land

## Final Assessment

This codebase already has real product substance. The main question is no longer "can it do useful things?" It can. The question is whether the repo can keep moving without accumulating too much integration drag.

My current read:

- product direction: strong
- backend capability: strong
- frontend workflow design: good and improving
- diagram migration: promising but still incomplete at repo level
- maintainability trend: acceptable now, but hotspot refactors should happen before another large feature wave

If this repo is treated as an internal platform and the team is willing to do one consolidation pass after the OpenFlowKit migration, it has a credible path to becoming a stable knowledge workspace rather than a perpetual feature branch.
