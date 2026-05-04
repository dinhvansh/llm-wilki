# Performance Baseline

Current baseline commands:

```powershell
python backend\scripts\benchmark_retrieval.py
python backend\scripts\evaluate_quality.py
powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1 -SkipBuild
powershell -ExecutionPolicy Bypass -File .\scripts\e2e_smoke.ps1
```

Current guardrails:

- Search result cap: `searchResultLimit` runtime setting.
- Graph node cap: `graphNodeLimit` runtime setting.
- Lint page scan cap: `lintPageLimit` runtime setting.
- Ingest jobs are durable rows and can be retried or canceled.
- Admin operations API exposes job backlog, failure count, and duration percentiles.

Production tuning targets:

- Keep global graph responses below the configured node cap.
- Keep lint scan caps aligned with scheduled maintenance windows.
- Enable PostgreSQL/pgvector for larger datasets.
- Use the retrieval benchmark after changing chunking, embeddings, or scorer weights.
