# Cloudflare Pages — 3-Project Setup

One git repo, three independent Cloudflare Pages projects. Each project points to the
same repo but uses a different **build command** and **output directory**.

---

## Project 1: App (`app.openflowkit.com`)

| Setting | Value |
|---|---|
| Repository | `Vrun-design/openflowkit` |
| Production branch | `main` |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Root directory | *(empty — repo root)* |
| Node version | `20` |

No environment variables required for a static build.
Add `VITE_OPENAI_BASE_URL` etc. if you wire AI proxy later.

---

## Project 2: Docs (`docs.openflowkit.com`)

| Setting | Value |
|---|---|
| Repository | `Vrun-design/openflowkit` |
| Production branch | `main` |
| Build command | `npm run build --workspace=docs-site` |
| Build output directory | `docs-site/dist` |
| Root directory | *(empty — repo root)* |
| Node version | `20` |

---

## Project 3: Landing (`openflowkit.com` / `www.openflowkit.com`)

| Setting | Value |
|---|---|
| Repository | `Vrun-design/openflowkit` |
| Production branch | `main` |
| Build command | `npm run build --workspace=web` |
| Build output directory | `web/dist` |
| Root directory | *(empty — repo root)* |
| Node version | `20` |

---

## Custom domains

After each project is created:

1. **App**: Pages project settings → Custom domains → add `app.openflowkit.com`
2. **Docs**: add `docs.openflowkit.com`
3. **Landing**: add `openflowkit.com` and `www.openflowkit.com`

Cloudflare handles SSL automatically for all domains on the same account.

---

## Free tier limits (as of 2025)

- 500 builds/month across all projects
- Unlimited bandwidth
- Unlimited sites
- All on the free plan — no credit card needed
