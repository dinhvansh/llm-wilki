# Frontend - LLM Wiki

Tài liệu này dành cho dev/frontend operator. Nếu mục tiêu là học cách dùng sản phẩm, đọc trước:

- [Hướng Dẫn Sử Dụng](../docs/HUONG_DAN_SU_DUNG.md)
- [Flow Nghiệp Vụ](../docs/FLOW_NGHIEP_VU.md)

## Vai trò của frontend

Frontend cung cấp các màn hình chính:

- dashboard
- sources
- pages
- review
- ask
- graph
- lint
- settings
- admin operations

## Setup

```powershell
npm install
Copy-Item .env.example .env.local
npm run dev
```

## Environment

| Variable | Mô tả |
|---|---|
| `NEXT_PUBLIC_USE_REAL_API` | bật dùng FastAPI backend |
| `NEXT_PUBLIC_API_BASE_URL` | base URL của API |

Ví dụ:

```env
NEXT_PUBLIC_USE_REAL_API=true
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
```

## Commands

```powershell
npm run dev
npm run build
npm run test:e2e
```

## Main routes

- `/`
- `/sources`
- `/pages`
- `/review`
- `/ask`
- `/graph`
- `/lint`
- `/settings`
- `/admin`

## Tài liệu liên quan

- [Flow Nghiệp Vụ](../docs/FLOW_NGHIEP_VU.md)
- [Release Notes](../RELEASE_NOTES.md)
