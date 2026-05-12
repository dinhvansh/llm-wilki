# Release Changeset - 2026-05-12

This file separates intentional release work from local research/temp files.

## Intentional Release Areas

- Backend storage foundation: `StorageObject`, MinIO/S3-compatible storage, source object download, artifact object linkage.
- Backend notes foundation: `Note`, `NoteAnchor`, `NoteVersion`, note CRUD, note search/Ask retrieval, note promotion actions.
- Ask quality: citation policy extraction, answer verifier diagnostics, citation precision quality gate.
- Permission hardening: business APIs use permission dependencies; admin bootstrap remains admin-only.
- Frontend evidence workflow: shared evidence card/drawer, Ask evidence verification, Ask citation drawer, Review evidence cards, Source chunk evidence cards, Page citation/backlink drawer, Graph node evidence actions.
- Docker/release: MinIO service, Redis host port moved to `56379`, Docker smoke fixed, backup smoke scripts added.

## Excluded From Release Package

- `_tmp_arkon/` is research/reference material and is ignored by `.gitignore`.
- Local SQLite databases, uploads, logs, and temp backup output remain ignored.

## Review Before Commit

- Group migrations and backend model/service/API changes together.
- Group frontend evidence/admin UX changes separately if creating multiple commits.
- Keep generated eval reports only if they are useful for release evidence.
