# Backend - LLM Wiki API

Tài liệu này dành cho dev/backend operator. Nếu mục tiêu là học cách dùng sản phẩm, đọc trước:

- [Hướng Dẫn Sử Dụng](../docs/HUONG_DAN_SU_DUNG.md)
- [Flow Nghiệp Vụ](../docs/FLOW_NGHIEP_VU.md)
- [Flow Xử Lý Hệ Thống](../docs/FLOW_XU_LY_HE_THONG.md)

## Vai trò của backend

Backend chịu trách nhiệm cho:

- source ingest
- worker jobs
- page generation/update/versioning
- review workflow
- ask/search/graph/lint
- auth/session/roles
- admin operations

## Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
python -m app.main
```

## Worker

```powershell
python -m app.worker
```

Smoke một job:

```powershell
python -m app.worker --once
```

## Environment chính

| Variable | Mô tả |
|---|---|
| `DATABASE_URL` | Kết nối PostgreSQL hoặc SQLite test |
| `REDIS_URL` | Redis cho worker notifications |
| `JOB_QUEUE_BACKEND` | `redis` hoặc `database` |
| `UPLOAD_DIR` | nơi lưu uploads local |
| `STORAGE_BACKEND` | hiện dùng `local`, reserved cho `s3` |
| `SECRET_KEY` | bắt buộc đổi trước production |

## Endpoint chính

- `/api/auth/*`
- `/api/sources/*`
- `/api/pages/*`
- `/api/review-items/*`
- `/api/ask*`
- `/api/search`
- `/api/lint*`
- `/api/admin/*`
- `/health`
- `/ready`

Docs API:

- Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Auth dev mặc định

- Email: `admin@local.test`
- Password: `admin123`

## Test

```powershell
python scripts\test_phase19.py
python scripts\test_phase20.py
python scripts\test_phase21.py
python -m compileall app migrations scripts
```

Regression đầy đủ từ root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_regression.ps1
```

## Tài liệu liên quan

- [Flow Xử Lý Hệ Thống](../docs/FLOW_XU_LY_HE_THONG.md)
- [Security Checklist](../SECURITY_CHECKLIST.md)
- [Performance Baseline](../PERFORMANCE_BASELINE.md)
- [Release Notes](../RELEASE_NOTES.md)
