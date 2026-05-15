---
name: bpm-flow-designer
description: Create or revise BPM/process diagrams as OpenFlowKit-compatible flow documents or OpenFlow DSL. Use when generating BPM flows from wiki pages, source documents, SOPs, policies, requirements, or process descriptions where the output must be ordered, traceable, and editable in OpenFlowKit.
---

# BPM Flow Designer

Create concise, reviewable BPM drafts that can be opened in OpenFlowKit without manual cleanup.

## Workflow

1. Identify the process trigger, final outcome, actors, systems, approvals, handoffs, exceptions, and source evidence.
2. Separate facts from gaps. Do not invent approvals, exception handling, SLAs, or actors; put missing logic in `metadata.openQuestions`.
3. Build the happy path first, then attach decision branches and exception paths.
4. Keep the layout left-to-right for business processes. Use one start node, explicit end nodes, and labeled decision branches.
5. Preserve source traceability with citations on metadata and, when available, node `data.citation` or `data.sourceRef`.

## Output Contract

Prefer OpenFlowKit flow document JSON when the caller asks for an editable diagram:

```json
{
  "version": "1.0",
  "engine": "openflowkit",
  "family": "flowchart",
  "pages": [
    {
      "id": "page-main",
      "name": "Main",
      "lanes": [],
      "nodes": [],
      "edges": [],
      "groups": [],
      "viewport": { "x": 0, "y": 0, "zoom": 1 }
    }
  ],
  "metadata": {
    "title": "",
    "objective": "",
    "owner": "",
    "scopeSummary": "",
    "openQuestions": [],
    "citations": []
  }
}
```

Node requirements:

- `id`: stable kebab-case or snake_case identifier.
- `type`: `start`, `task`, `decision`, `handoff`, `subprocess`, or `end`.
- `label`: short action phrase; decisions should read as a question.
- `owner`: actor, team, or `System`.
- `position`: use deterministic coordinates.
- `size`: default to `{ "width": 220, "height": 72 }`.

Edge requirements:

- Use `source`, `target`, `type`, and optional `label`.
- Decision nodes must have at least two outgoing labeled edges such as `Approve`/`Reject`, `Yes`/`No`, or `Pass`/`Fail`.
- Connect exception paths to a rejection/rework/end node instead of leaving them floating.

## Layout

Use a left-to-right grid:

- Start at `x=80`, `y=120`.
- Increase `x` by `280` for each process step.
- Put actors/lanes on separate `y` bands, spaced by `160`.
- For branches from the same decision, stack branch nodes vertically with at least `90` pixels between them.
- Keep the happy path near the top and exception paths below it.
- Avoid edge crossings by merging branches only after the branch tasks.

## BPM Quality Bar

Before returning the diagram, check:

- The first node is a start node and every normal path reaches an end node.
- Every task has an owner.
- Every decision has two labeled outgoing edges.
- The node order matches the source procedure order.
- Unsupported assumptions are listed as open questions.
- Citations remain attached to the diagram metadata.
