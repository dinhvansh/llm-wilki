# AI-native Wiki Platform

`llm-wiki` is an internal knowledge workspace that turns scattered documents into a grounded wiki with citations, review flows, scoped access control, and evidence-aware Ask AI.

The current build is not a CRUD dashboard. It is a connected workflow:

- `Sources -> ingest -> chunks / claims / artifacts`
- `Ask AI -> citation -> source -> page -> graph`
- `Notes / review / draft pages -> publish`

## What is in this repo

Core product capabilities already implemented:

- source ingest from `file`, `URL`, `text`, and `transcript`
- durable background jobs with worker, retry, cancel, logs, and progress
- collection-scoped authorization with roles, memberships, and permission engine
- grounded Ask AI with citations, related pages, related sources, diagnostics, and feedback logging
- multimodal evidence flow for OCR, notebook context, structure, table, and image-derived artifacts
- first-class notes with anchors to citations, chunks, artifacts, pages, and review items
- pages with backlinks, evidence panels, revision history, and audit trail
- review queue with approve / reject / merge / comments
- graph, lint, diagrams, admin operations, skills, and release smoke scripts

## Current runtime behavior

Ask AI supports two modes:

- `provider-backed`: Ollama / OpenAI / compatible provider is configured for answer generation and embeddings
- `grounded fallback`: if no provider is configured, the system still answers from retrieval + rerank + formatting logic with citations

If you run Ollama locally, recommended setup is:

- answer tasks: `provider=ollama`, model such as `gemma3:4b`
- embeddings: `provider=ollama`, model `nomic-embed-text`
- Docker base URL: `http://host.docker.internal:11434`

## Stack

- `llm-wiki/`: Next.js 15 frontend
- `backend/`: FastAPI API, Alembic migrations, worker services
- `postgres`: PostgreSQL + pgvector
- `redis`: queue / worker coordination
- `minio`: S3-compatible object storage for source and artifact storage
- `drawio`: self-hosted diagram editor

## Quick start with Docker

1. Create backend env:

```powershell
Copy-Item backend\.env.example backend\.env
```

2. Start the full stack:

```powershell
docker compose up -d --build
```

3. Open the app:

- frontend: `http://localhost:3100`
- backend API: `http://localhost:18000`
- Swagger: `http://localhost:18000/docs`
- draw.io: `http://localhost:18081`
- MinIO console: `http://localhost:19001`

Default dev account:

- email: `admin@local.test`
- password: `admin123`

## Local development

### Backend

```powershell
cd backend
pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
python -m app.main
```

### Worker

```powershell
cd backend
python -m app.worker
```

### Frontend

```powershell
cd llm-wiki
npm install
Copy-Item .env.example .env.local
npm run dev
```

## Verification commands

Build frontend:

```powershell
npm --prefix llm-wiki run build
```

Run Ask quality eval:

```powershell
python backend\scripts\evaluate_quality.py
```

Run retrieval benchmark:

```powershell
python backend\scripts\benchmark_retrieval.py
```

Run Docker smoke:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1 -SkipBuild
```

Run backup / restore smoke:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\backup_restore_smoke.ps1
```

Run full clean reset from empty volumes:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\clean_seed_reset.ps1 -Apply
```

Run broader regression:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_regression.ps1
```

## Repository map

- [backend/README.md](backend/README.md)
- [docs/upgrade-roadmap-2026.md](docs/upgrade-roadmap-2026.md)
- [docs/ai-knowledge-workspace-gap-plan-2026.md](docs/ai-knowledge-workspace-gap-plan-2026.md)
- [docs/QUALITY_RELEASE_CHECKLIST.md](docs/QUALITY_RELEASE_CHECKLIST.md)
- [docs/PRODUCTION_RELEASE_CHECKLIST.md](docs/PRODUCTION_RELEASE_CHECKLIST.md)
- [docs/ASK_AI_DOCUMENT_QA_TEST_CASES.md](docs/ASK_AI_DOCUMENT_QA_TEST_CASES.md)

## Release status

This repo has already been verified on local Docker for:

- clean stack reset from empty volumes
- Postgres + MinIO backup smoke
- grounded Ask AI quality gates
- retrieval benchmark gates
- scoped permissions and admin flows

Residual work should be tracked in:

- [docs/upgrade-roadmap-2026.md](docs/upgrade-roadmap-2026.md)
- [docs/ai-knowledge-workspace-gap-plan-2026.md](docs/ai-knowledge-workspace-gap-plan-2026.md)
