# LLM Wiki

LLM Wiki la mot nen tang wiki noi bo co AI ho tro, dung de bien tai lieu roi rac thanh knowledge base co cau truc, co citation, co review, va co van hanh duoc tren Docker/local.

## Du an hien dang co gi

Build hien tai da co cac khoi chuc nang chinh:

- ingest source tu `file`, `URL`, `text`, `transcript`
- durable jobs voi `worker`, `retry`, `cancel`, `job logs`, `progress`
- collections, source suggestions, archive/restore source, refresh URL source
- generated pages co citation, backlink, version history, audit trail
- optimistic edit conflict detection va restore version cu thanh draft moi
- review queue voi approve/reject/merge, issue-page creation, comment thread
- Ask AI grounded voi citations, chat history, save answer as draft
- search/ask diagnostics, lint quality layer, knowledge graph
- auth/session/roles: `admin`, `reviewer`, `editor`, `reader`
- admin operations dashboard/API, config export/import, bulk retry failed jobs
- huong mo rong diagram/process se dung `draw.io` open-source theo mo hinh self-host, khong phu thuoc editor online

Trang thai hien tai: `0.1.0-alpha` cho noi bo. Chi tiet nam o [RELEASE_NOTES.md](RELEASE_NOTES.md).

## Kien truc

- `llm-wiki/`: frontend Next.js 15
- `backend/`: FastAPI API + Alembic migrations + worker
- `postgres`: PostgreSQL + pgvector image cho Docker stack
- `redis`: channel thong bao worker
- `backend_data`: volume luu uploads local-first

## Chay nhanh bang Docker

1. Tao env cho backend:

```powershell
Copy-Item backend\.env.example backend\.env
```

2. Start stack:

```powershell
docker compose up -d --build postgres redis drawio backend worker frontend
```

3. Mo he thong:

- Frontend: http://localhost:3100
- Backend: http://localhost:8000
- Self-hosted draw.io: http://localhost:8081
- Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Tai khoan dev mac dinh:

- Email: `admin@local.test`
- Password: `admin123`

## Chay local khong dung Docker

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

## Lenh quan trong

### Recreate Docker stack

```powershell
docker compose up -d --build --force-recreate postgres redis drawio backend worker frontend
```

### Regression day du

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_regression.ps1
```

### Docker smoke

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1 -SkipBuild
```

### E2E smoke

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e_smoke.ps1
```

### Reset local Docker

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\reset_local.ps1
```

## Tai lieu nen doc

### Neu ban muon dung he thong

1. [Huong Dan Su Dung](docs/HUONG_DAN_SU_DUNG.md)
2. [Flow Nghiep Vu](docs/FLOW_NGHIEP_VU.md)
3. [Flow Xu Ly He Thong](docs/FLOW_XU_LY_HE_THONG.md)
4. [BPM Flow Standard](docs/BPM_FLOW_STANDARD.md)

### Neu ban muon dev

1. [Backend README](backend/README.md)
2. [Frontend README](llm-wiki/README.md)
3. [Update Plan](UPDATE_PLAN_2.md)

Cach doc nhanh:

- mo phan `Quick Status` o dau [UPDATE_PLAN_2.md](UPDATE_PLAN_2.md) de xem phase nao da xong va duoc verify tren local/Docker/E2E den dau
- moi phase trong plan da duoc rut gon theo 2 muc: `Implementation log` va `Verification`
- neu can biet trang thai verify gan nhat, uu tien cac dong co moc `2026-05-04`

### Neu ban muon van hanh/release

1. [Release Notes](RELEASE_NOTES.md)
2. [Security Checklist](SECURITY_CHECKLIST.md)
3. [Performance Baseline](PERFORMANCE_BASELINE.md)

## Luong su dung thuc te

Flow thong dung cua du an:

1. ingest source
2. worker xu ly -> chunk/claim/entity/page/suggestion
3. editor kiem tra source detail va xu ly suggestions
4. editor sua draft page, bo sung citation/backlink neu can
5. reviewer approve/reject/merge
6. publish
7. lint/graph/admin operations de maintenance

## Backup va restore

Huong dan backup/restore DB va uploads hien duoc ghi o:

- [backend/README.md](backend/README.md)
- [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md)

## Known limitations

Nhung diem chua xong trong build alpha:

- chua co realtime multi-user editing
- S3 storage moi dung o muc config placeholder, adapter active van la local
- draw.io editor da self-host va luu `drawio_xml`, nhung visual QA editor flow van nen tiep tuc mo rong khi dua len production
- aggregate metrics cho token/latency cua provider chua persist day du

Chi tiet xem them o [RELEASE_NOTES.md](RELEASE_NOTES.md).
