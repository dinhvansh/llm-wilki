# AI-native Wiki Platform

Internal knowledge workspace with grounded Ask AI, citations, review workflows, scoped permissions, and diagram support.

## 1) What You Get

- Source ingest: file, URL, text, transcript
- Background jobs: queue, retry, progress, cancel
- Ask AI: grounded answers, citations, evidence diagnostics
- Review + governance: lint, review queue, notes/anchors
- Pages + graph + timeline + glossary + entity explorer
- Embedded OpenFlowKit for process/diagram workflows

## 2) Architecture

- `llm-wiki/` - Next.js frontend
- `backend/` - FastAPI API + worker
- `postgres` - database (pgvector)
- `redis` - queue coordination
- `minio` - object storage
- `openflowkit` - embedded diagram app

## 3) Prerequisites (Cross-Platform)

### Recommended (works on most machines)

- Docker Desktop (or Docker Engine + Compose plugin)
  - Verify: `docker --version` and `docker compose version`

### Optional for local non-Docker development

- Python 3.11+
- Node.js 20+
- npm 10+

## 4) Quick Start (Docker-first)

This is the default path for Windows/macOS/Linux.

1. Clone repo and open project root.
2. Create backend env:

```bash
cp backend/.env.example backend/.env
```

PowerShell:

```powershell
Copy-Item backend\.env.example backend\.env
```

3. Start stack:

```bash
docker compose up -d --build
```

4. Verify stack health:

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1
```

5. Open:

- App: `http://localhost:3100`
- Backend docs: `http://localhost:18000/docs`
- OpenFlowKit: `http://localhost:3045`
- MinIO console: `http://localhost:19001`

Default account:

- Email: `admin@local.test`
- Password: `admin123`

## 5) Service Ports

- Frontend: `3100`
- Backend API: `18000`
- OpenFlowKit: `3045`
- Postgres: `55432`
- Redis: `56379`
- MinIO API: `19000`
- MinIO Console: `19001`

## 6) Local Dev (without Docker)

Use this only when you need direct debugging by service.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m app.main
```

PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
python -m app.main
```

### Worker

```bash
cd backend
python -m app.worker
```

### Frontend

```bash
cd llm-wiki
npm install
cp .env.example .env.local
npm run dev
```

PowerShell:

```powershell
cd llm-wiki
npm install
Copy-Item .env.example .env.local
npm run dev
```

## 7) Ask AI Runtime Modes

- Provider-backed: uses configured LLM/embedding providers
- Grounded fallback: deterministic grounded formatting when provider path is unavailable

### RAG Answer Policy

Ask responses expose:

- `answerMode`: `answer | partial_answer | no_answer | general_fallback`
- `evidenceStatus`: `supported | partial | insufficient | unsupported`
- `answerLanguage` + `sourceLanguages`
- `evidenceGate` + verifier diagnostics

Runtime knobs in `/settings`:

- `minimumTopScore`
- `minimumTermCoverage`
- `allowPartialAnswers`
- `allowGeneralFallback` (default `false`)
- `crossLingualRewriteEnabled` (default `true`)

## 8) Validation Commands

### Build checks

```bash
python -m compileall backend/app
npm --prefix llm-wiki run build
```

### E2E (frontend)

```bash
npm --prefix llm-wiki run test:e2e
```

### Smoke (docker stack)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1 -SkipBuild
powershell -ExecutionPolicy Bypass -File .\scripts\e2e_smoke.ps1
```

## 9) Troubleshooting

- Port conflict:
  - Stop old containers/apps using `3100/18000/3045/...`
- Backend 500 after config change:
  - `docker compose logs backend --tail=200`
- Rebuild clean:
  - `docker compose down`
  - `docker compose up -d --build`
- Full reset:
  - `powershell -ExecutionPolicy Bypass -File .\scripts\clean_seed_reset.ps1 -Apply`

## 10) Repo Map

- Backend guide: [backend/README.md](backend/README.md)
- Frontend guide: [llm-wiki/README.md](llm-wiki/README.md)
- Upgrade roadmap: [docs/upgrade-roadmap-2026.md](docs/upgrade-roadmap-2026.md)
- Quality checklist: [docs/QUALITY_RELEASE_CHECKLIST.md](docs/QUALITY_RELEASE_CHECKLIST.md)
- Production checklist: [docs/PRODUCTION_RELEASE_CHECKLIST.md](docs/PRODUCTION_RELEASE_CHECKLIST.md)
