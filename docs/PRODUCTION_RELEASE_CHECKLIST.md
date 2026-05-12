# Production Release Checklist

Date: 2026-05-12

## Required Environment

- [ ] Replace dev admin password before public/shared deployment.
- [ ] Set a strong auth/session secret.
- [ ] Lock CORS to approved origins.
- [ ] Set production database URL.
- [ ] Set S3/MinIO credentials outside source control.
- [ ] Configure upload size limits and accepted MIME types.
- [ ] Configure backup retention for Postgres and MinIO.
- [ ] Configure log retention and audit export location.

## Verification

- [ ] `python -m compileall backend/app backend/migrations backend/scripts`
- [ ] `python backend/scripts/evaluate_quality.py`
- [ ] `python backend/scripts/benchmark_retrieval.py`
- [ ] `npm --prefix llm-wiki run build`
- [ ] `powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1`
- [ ] Manual login smoke: admin, reader, editor, reviewer.
- [ ] Manual Ask smoke: grounded answer, citation drawer, save note.
- [ ] Manual source smoke: upload, ingest, storage object, download.
- [ ] Manual review smoke: evidence card, ask scoped, approve/reject permission.

## Release Blockers

- [ ] No unreviewed temp research folders in release package.
- [ ] No dev-only credentials in committed env examples.
- [ ] No failing quality gates.
- [ ] No unauthenticated sensitive endpoints.
- [ ] Backup and restore process documented.
