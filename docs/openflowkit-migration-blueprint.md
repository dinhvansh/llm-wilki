# OpenFlowKit Migration Blueprint

## Decision

The diagrams module will move to one engine only: an OpenFlowKit-style flow engine.

`drawioXml` stops being the runtime source of truth. Existing draw.io data is kept only for one-time migration and compatibility inspection during the transition. After migration, the app reads and writes an OpenFlow document model.

## Why Change

The current module is split between two ideas:

- The backend already generates structured BPM data in `specJson`.
- The editor and versions still revolve around `drawioXml`.

That makes AI generation harder than it needs to be. AI should produce a structured flow model directly. The renderer/editor should consume that model directly. XML should not be the core authoring format.

OpenFlowKit is a better target model because it is built around:

- visual canvas editing
- diagram-as-code / structured diagram state
- Mermaid and structured imports
- AI generation directly onto the canvas
- local-first document behavior
- export formats derived from the document model

Reference: https://github.com/Vrun-design/openflowkit

## Current State

Frontend:

- `llm-wiki/src/app/(main)/diagrams/page.tsx`
- `llm-wiki/src/app/(main)/diagrams/[slug]/page.tsx`
- `llm-wiki/src/components/diagram/drawio-embed.tsx`

Backend:

- `backend/app/models/records.py`
- `backend/app/api/diagrams.py`
- `backend/app/services/diagrams.py`
- `backend/app/schemas/diagram.py`

Current storage:

- `diagrams.drawio_xml`
- `diagrams.spec_json`
- `diagram_versions.drawio_xml`
- `diagram_versions.spec_json`

Current AI generation:

- `bpm_generation` profile creates BPM-ish `specJson`
- backend converts `specJson` into `drawioXml`
- frontend embeds draw.io for editing

## Target Architecture

### Source Of Truth

Add an OpenFlow document model as the only active diagram state:

```json
{
  "version": "1.0",
  "family": "flowchart",
  "pages": [
    {
      "id": "page-main",
      "name": "Main",
      "nodes": [],
      "edges": [],
      "groups": [],
      "viewport": {}
    }
  ],
  "metadata": {
    "title": "",
    "objective": "",
    "owner": "",
    "sourceIds": [],
    "sourcePageIds": [],
    "reviewStatus": "needs_review"
  }
}
```

The exact model should be aligned after auditing OpenFlowKit internals, but these concepts must exist:

- document
- pages
- nodes
- edges
- groups or lanes
- viewport
- metadata
- validation
- traceability

### Database

Replace active usage of `drawio_xml` with `flow_document`.

Recommended additive migration first:

- `diagrams.flow_document JSON`
- `diagram_versions.flow_document JSON`
- keep `drawio_xml` columns temporarily but stop writing them in normal flows

Final cleanup after migration:

- remove draw.io editor usage
- stop returning `drawioXml` as a required frontend field
- keep export-only compatibility separately if needed

### Backend Service

Refactor `backend/app/services/diagrams.py` around these operations:

- `create_flow`
- `update_flow_document`
- `generate_flow_from_page`
- `generate_flow_from_source`
- `validate_flow_document`
- `serialize_flow`
- `snapshot_flow_version`

Remove `_drawio_xml_from_spec` from the live path. It can remain temporarily as a migration helper only.

### AI Generation

AI should output OpenFlow JSON, not draw.io XML.

Prompt target:

```text
Return strict OpenFlow document JSON.
Use nodes, edges, groups, metadata, reviewStatus, citations, and openQuestions.
Do not invent actors, branches, or exception paths.
If the source is ambiguous, preserve ambiguity in openQuestions.
```

Validation must run after model output:

- required start/end node checks
- missing owner checks
- decision branch checks
- orphan edge checks
- citation coverage checks
- review warnings

### Frontend Editor

Replace the current detail page with a canvas-first workspace:

- left rail: diagrams list, pages/layers, source links
- center: OpenFlow canvas
- right panel: properties, review, citations, validation
- bottom or side studio: AI prompt, Mermaid/import, JSON/code view
- toolbar: add node, connect, layout, undo/redo, zoom, export

The route remains:

- `/diagrams`
- `/diagrams/[slug]`

The underlying editor changes completely.

### Import And Export

Supported import targets:

- OpenFlow JSON
- Mermaid
- legacy draw.io XML migration

Supported export targets:

- OpenFlow JSON
- Mermaid
- PNG/SVG
- later: animated export if practical

Do not keep draw.io as an editor engine.

## Migration Plan

### Phase 1: Audit OpenFlowKit Internals

Goal: identify what can be reused directly.

Tasks:

- inspect OpenFlowKit data model
- inspect canvas/editor components
- inspect Mermaid parser and DSL sync
- inspect export pipeline
- check licenses and package boundaries
- decide whether to vendor selected modules or rebuild compatible pieces

Output:

- selected model shape
- selected packages/components to reuse
- list of code that must be rewritten locally

### Phase 2: Backend Model Cutover

Goal: introduce `flow_document` without changing user behavior yet.

Tasks:

- add `flow_document` to `Diagram`
- add `flow_document` to `DiagramVersion`
- update serializers with `flowDocument`
- create migration function from current `specJson` to `flowDocument`
- keep `drawioXml` read-only for old records

Done when:

- existing diagrams return a valid `flowDocument`
- new diagrams write `flowDocument`
- versions snapshot `flowDocument`

### Phase 3: AI Output Cutover

Goal: stop generating draw.io XML.

Tasks:

- update BPM generation prompt to OpenFlow JSON
- map heuristic generation to OpenFlow JSON
- validate OpenFlow document server-side
- preserve citations and open questions in metadata
- remove live call to `_drawio_xml_from_spec`

Done when:

- generating from page/source creates a canvas-ready OpenFlow document
- validation warnings appear without requiring draw.io

### Phase 4: Editor Replacement

Goal: replace `/diagrams/[slug]` UI with OpenFlow editor.

Tasks:

- remove `DrawioEmbed` from the page
- build/import OpenFlow canvas shell
- bind canvas changes to `flowDocument`
- add properties panel
- add source/citation panel
- add AI studio panel
- add autosave and version conflict handling

Done when:

- user can create, edit, save, review, publish, and restore versions using the new editor only

### Phase 5: List And Creation UX

Goal: make `/diagrams` a flow workspace, not a card list with a prompt.

Tasks:

- replace `window.prompt`
- add create modal/workspace
- support blank flow, AI-generated flow, Mermaid import, source/page generated flow
- add recent flows, status filters, collection filters
- show validation/review status clearly

Done when:

- creating a flow no longer depends on draw.io or ad hoc prompts

### Phase 6: Legacy Data Cleanup

Goal: remove draw.io from active code.

Tasks:

- migrate existing records to `flowDocument`
- stop exposing `drawioXml` in frontend contracts except legacy export endpoint
- remove `DrawioEmbed`
- remove live draw.io autosave state
- remove draw.io XML editing textarea
- keep an admin-only legacy inspector if needed

Done when:

- normal product flow has one engine only
- draw.io is not loaded by the frontend

## API Changes

Current update payload:

```json
{
  "specJson": {},
  "drawioXml": ""
}
```

Target update payload:

```json
{
  "flowDocument": {},
  "changeSummary": "",
  "expectedVersion": 1
}
```

New endpoints to consider:

- `POST /api/diagrams/import/mermaid`
- `POST /api/diagrams/{id}/layout`
- `POST /api/diagrams/{id}/validate`
- `POST /api/diagrams/{id}/ai-edit`
- `GET /api/diagrams/{id}/export/mermaid`
- `GET /api/diagrams/{id}/export/json`

## Compatibility Rules

During migration:

- existing `specJson` can generate `flowDocument`
- existing `drawioXml` is not edited
- any diagram without `flowDocument` is upgraded on read or via migration job

After migration:

- `flowDocument` is required
- AI generation outputs `flowDocument`
- editor writes `flowDocument`
- versioning stores `flowDocument`
- review/publish reads `flowDocument`

## Risk Areas

Main risks:

- OpenFlowKit internals may not be packaged for direct reuse
- canvas editor integration can be larger than expected
- old draw.io diagrams may not round-trip cleanly
- export feature parity may take multiple passes
- frontend bundle size may grow if vendoring too much

Mitigations:

- start with the document model and generation pipeline
- reuse only selected modules after audit
- keep migration one-way
- ship editor replacement behind the same `/diagrams` routes only when create/edit/save passes
- maintain version snapshots throughout

## First Implementation Slice

The first code slice should be backend-first:

1. Add `flow_document` columns.
2. Add `FlowDocument` TypeScript type.
3. Add `specJson -> flowDocument` converter.
4. Return `flowDocument` in `Diagram`.
5. Update create/generate to write `flowDocument`.
6. Keep old UI working for one commit while backend stabilizes.

Second slice:

1. Replace `/diagrams/[slug]` with a simple OpenFlow canvas shell.
2. Render nodes/edges from `flowDocument`.
3. Allow add/edit/delete node and edge.
4. Save `flowDocument`.

Third slice:

1. Add AI studio.
2. Add Mermaid import.
3. Add validation panel.
4. Remove draw.io from live UI.

## Definition Of Done

The migration is complete when:

- `/diagrams` creates OpenFlow documents.
- `/diagrams/[slug]` edits OpenFlow documents.
- AI generation writes OpenFlow documents.
- versions store OpenFlow documents.
- review and publish use OpenFlow documents.
- no normal route loads draw.io.
- `drawioXml` is not part of the active create/edit/save path.
