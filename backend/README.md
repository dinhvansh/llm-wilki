# Backend - AI-native Wiki API

This guide is for backend development and local operations.

If you want product usage or workflow context first, read:

- [User Guide](../docs/HUONG_DAN_SU_DUNG.md)
- [Business Flow](../docs/FLOW_NGHIEP_VU.md)
- [System Flow](../docs/FLOW_XU_LY_HE_THONG.md)

## Responsibilities

The backend owns:

- source ingest
- worker jobs and job status
- retrieval, Ask AI, and search
- page generation, versioning, and review
- notes, citations, and evidence workflows
- auth, roles, permissions, and collection scope
- admin and runtime settings
- durable storage metadata and file download flows

## Local setup

Recommended from repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_local_backend.ps1
```

Manual setup:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
python -m app.main
```

## Worker

```powershell
cd backend
python -m app.worker
```

Run a single-pass worker locally:

```powershell
python -m app.worker --once
```

## OCR note for Windows

Local OCR for scanned PDFs and image sources requires:

- `Tesseract`
- `Docling`

The repo prefers `backend\.local\tessdata` for local language files.

Quick verification:

```powershell
.\.venv\Scripts\python.exe scripts\test_phase28.py
```

## Main environment variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL or SQLite connection string |
| `REDIS_URL` | Redis for queue and notifications |
| `JOB_QUEUE_BACKEND` | `redis` or `database` |
| `UPLOAD_DIR` | local upload cache / file path |
| `STORAGE_BACKEND` | `local` or `s3` |
| `S3_ENDPOINT_URL` | MinIO/S3 endpoint |
| `S3_BUCKET` | object storage bucket |
| `SECRET_KEY` | app secret; change before shared/prod use |

## Main endpoints

- `/api/auth/*`
- `/api/sources/*`
- `/api/pages/*`
- `/api/review-items/*`
- `/api/notes/*`
- `/api/ask*`
- `/api/search`
- `/api/diagrams/*`
- `/api/lint*`
- `/api/admin/*`
- `/health`
- `/ready`

API docs:

- Swagger: `http://localhost:18000/docs`
- ReDoc: `http://localhost:18000/redoc`

## Default local auth

- email: `admin@local.test`
- password: `admin123`

## Useful commands

Compile backend code:

```powershell
python -m compileall app migrations scripts
```

Run targeted quality checks:

```powershell
python scripts\benchmark_retrieval.py
python scripts\evaluate_quality.py
```

Run broader regression from repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_regression.ps1
```

## Related docs

- [System Flow](../docs/FLOW_XU_LY_HE_THONG.md)
- [Security Checklist](../SECURITY_CHECKLIST.md)
- [Performance Baseline](../PERFORMANCE_BASELINE.md)
- [Release Notes](../RELEASE_NOTES.md)
