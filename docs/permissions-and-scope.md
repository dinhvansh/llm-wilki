# Permissions And Scope Policy

Date: 2026-05-12

## Scope Model

`llm-wiki` uses three practical visibility levels:

- `global`: workspace-wide operational/configuration data.
- `workspace`: knowledge visible to authenticated users unless collection scope restricts them.
- `collection`: knowledge tied to one collection and filtered by collection membership when a user is restricted.

Department is currently a user organization field for administration, filtering, and reporting. It is not yet a hard data-isolation boundary.

## Global Roles

System roles are intentionally simple:

- `reader`: read knowledge, Ask AI, saved views, and private notes.
- `editor`: reader permissions plus source/page/diagram/note write workflows.
- `reviewer`: editor permissions plus review approval and settings read.
- `admin`: all permissions and user/department/collection administration.

Custom role authoring is not enabled yet. The Roles page is a permission catalog for the current system roles.

## Collection Membership

Collection membership roles are:

- `viewer`: can read collection-scoped knowledge.
- `contributor`: reserved for future scoped contribution flows.
- `editor`: can edit collection-scoped knowledge when global role also permits the action.
- `admin`: collection-level ownership semantics for future delegation.

If a user has no collection memberships, they are treated as workspace-wide for the current internal deployment model. If a user has memberships, query-time filtering restricts collection-scoped records to those memberships while still allowing unscoped workspace knowledge.

## API Enforcement

Business APIs should use `require_permission("resource:action")`.

Admin bootstrap and high-risk administration APIs remain explicit `require_roles("admin")` boundaries:

- user creation/update/password reset
- department administration
- global audit/config import/export
- destructive collection delete

## UI Enforcement

Frontend gating should hide or disable create/edit/delete actions when the actor lacks permission. Backend enforcement remains authoritative; UI gating is a usability layer, not a security layer.

## Release Rule

Before release, every new endpoint must document one of:

- permission dependency
- admin-only boundary
- authenticated read-only exception with justification
