# Frontend - AI-native Wiki

This guide is for frontend development and local runtime setup.

If you want product usage or workflow context first, read:

- [User Guide](../docs/HUONG_DAN_SU_DUNG.md)
- [Business Flow](../docs/FLOW_NGHIEP_VU.md)

## Responsibilities

The frontend provides the main workspace surfaces:

- dashboard
- collections
- sources
- pages
- Ask AI
- graph
- review
- lint
- settings
- admin operations
- diagram flows through embedded OpenFlowKit

## Local setup

```powershell
cd llm-wiki
npm install
Copy-Item .env.example .env.local
npm run dev
```

## Main environment variables

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_USE_REAL_API` | enable FastAPI backend instead of mock services |
| `NEXT_PUBLIC_API_BASE_URL` | browser API base URL |
| `NEXT_PUBLIC_OPENFLOWKIT_URL` | iframe URL for the OpenFlowKit editor |
| `OPENFLOWKIT_PROXY_TARGET` | server-side proxy target for `/openflowkit` |
| `API_PROXY_TARGET` | server-side proxy target for `/backend-api` |

Example:

```env
NEXT_PUBLIC_USE_REAL_API=true
NEXT_PUBLIC_API_BASE_URL=/backend-api
NEXT_PUBLIC_OPENFLOWKIT_URL=/openflowkit/#/home
API_PROXY_TARGET=http://localhost:18000/api
OPENFLOWKIT_PROXY_TARGET=http://localhost:3045
```

## Commands

```powershell
npm run dev
npm run build
npm run test:e2e
```

## Main routes

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
- `/diagrams`
- `/diagram-flow/[slug]`
- `/admin/*`

## Related docs

- [Business Flow](../docs/FLOW_NGHIEP_VU.md)
- [Release Notes](../RELEASE_NOTES.md)
