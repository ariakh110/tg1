---
id: SPEC-local-engineering-flow
companions:
  - ../../../LANGGRAPH.fa.md
  - ../../../LANGGRAPH-ARCHITECTURE.md
sources: []
---

# Local engineering phase coordination

## Why

Aria wants document-driven engineering across Claude Code and Codex without losing phase state, accepted decisions or review evidence when switching sessions. BMAD supplies the methodology; a local LangGraph runner maintains execution checkpoints while the current assistant performs the work.

## Capabilities

- **CAP-1**
  - **intent:** Resume the same work in another session or coding tool.
  - **success:** The same task ID loads its pending stage and checkpoint after process restart, and a duplicate start cannot overwrite it.
- **CAP-2**
  - **intent:** Keep human design and implementation decisions explicit.
  - **success:** A normal work receipt cannot advance either approval gate; an explicit human decision and its evidence must be recorded separately.
- **CAP-3**
  - **intent:** Associate progress with real artifacts and revise without silently retaining obsolete approvals.
  - **success:** Changed hashes, stale checkpoints, empty artifacts, secret paths and repository escape are rejected; backward revision discards downstream current records and preserves history.
- **CAP-4**
  - **intent:** Follow the agreed BMAD phases through implementation and two review perspectives.
  - **success:** The documented sequence completes with receipts; a failed spec or quality review returns to implementation, and design rejection returns to architecture.

## Constraints

- Current Claude/Codex sessions execute work; the runner makes no model API calls, executes no shell commands, launches no agents and disables tracing for its graph operations.
- Keep product runtime dependencies, schemas and server deployment unchanged. Developer dependencies use a separate environment and committed version lock.
- Preserve OpenSpec as the product requirements authority and link BMAD specs to it when product changes are proposed.
- One trusted local writer owns the SQLite checkpoint store. The CLI records operator evidence; it is not multi-user authentication or independent proof that reported tests passed.
- Preserve prior explicit approval for the same artifacts; do not manufacture approval or ask for an identical decision twice.

## Non-goals

- A hosted agent service, autonomous model execution, distributed multi-user orchestration or a new ERP module.
- Automatic production deployment, real provider sends or a paid model integration.

## Success signal

Local tests and a cross-process CLI demonstration resume the same task through the backend and frontend launchers. Stage receipts and human decisions survive restarts, while stale or changed inputs cannot silently advance.

## Assumptions

- The operator and local checkpoint files are trusted. Shared state across different devices requires an explicit transfer or a future persistence service.
