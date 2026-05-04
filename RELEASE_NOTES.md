# Release Notes

## 0.1.0-alpha - 2026-04-23

### Included

- Source ingest for files, URL, pasted text, and transcript-style text.
- Durable ingest/rebuild jobs with worker, retry, cancel, job logs, progress, and Docker smoke path.
- Collections, source suggestions, source archive/restore, and source refresh for URL sources.
- Generated wiki pages with citations, backlinks, version history, audit trail, publish/unpublish, restore version, and optimistic edit conflict detection.
- Review queue with approve/reject/merge, issue-page creation, and comment threads.
- Ask AI with grounded citations, persistent chat history, and save-answer-as-draft.
- Search/Ask diagnostics, retrieval limits, graph limits, lint scan limits, and benchmark/eval scripts.
- Auth/session model with admin/editor/reviewer/reader roles and dev admin seed user.
- Admin operations dashboard/API with request ids, structured logs, job metrics, audit filter, config export/import, and bulk retry.
- Connector registry, local-first storage abstraction, checksum dedupe metadata, and S3-compatible config placeholders.
- Docling parsing with Tesseract OCR (`eng`, `vie`), structure-aware chunking, schema-based claim extraction, knowledge units, extraction runs, and task-scoped AI settings.
- Self-hosted draw.io integration with persisted `drawio_xml`, diagram versions, review workflow, and BPM traceability panels.

### Known Limitations

- Realtime multi-user editing is not implemented; Phase 19 uses optimistic locking and non-realtime comments.
- S3 storage is configured as a portability target, but the active storage adapter is local-only.
- LLM token and provider latency aggregation is exposed as a metrics contract but depends on provider clients returning usage metadata.
- Visual QA is covered by Playwright route smoke/build checks in this environment; browser screenshot MCP was unavailable during Phase 18.

### Short-Term Roadmap

- Add concrete S3/MinIO adapter implementation.
- Persist aggregate retrieval and LLM usage metrics.
- Expand frontend collaboration controls and richer visual QA around diagram editing flows.
- Add CI pipeline that runs migrations, backend scripts, frontend build, Docker smoke, and Playwright smoke.
