# LangGraph workflow adoption handoff (2026-10-27)

## Objective and decision
User explicitly selected local LangGraph stage/approval tracking with work performed by existing Claude Code/Codex sessions. No model API or unattended provider integration requested.

## Implementation
Backend tools/engineering_flow is the single standalone runner; tools/engineering.ps1 in both repos locates it. SQLite state lives in the ignored backend .engineering-state directory. Isolated uv project/lock; product dependencies and schemas unchanged. Shared skills/WORKFLOW now route substantial engineering work through the pending graph stage.

## Design
Backend BMAD spec: docs/engineering/bmad-output/specs/spec-local-engineering-flow/SPEC.md and append-only .memlog.md. Operating guide: LANGGRAPH.fa.md; code-derived diagrams: LANGGRAPH-ARCHITECTURE.md.

## Validation
9 unit tests passed (restart, duplicate/stale receipts, gates, hash changes, path/secret/empty artifact rejection, revision, review failure, concurrent lock and no network calls). CLI smoke across backend and frontend processes passed: start, shared state read, artifact submission, restart and rejected approval outside a gate. Both 46-skill/300-file mirror checks passed. Dependencies installed and pinned using uv; tracing disabled for graph operations.

## Limits and next action
No live Claude session was invoked; file/CLI integration verified. The local operator reports evidence; this is not multi-user authentication or independent proof tests ran. No product module was chosen or started. Start a named task for the next substantial request, then follow its pending stage. Existing unrelated frontend HANDOFF.md and PURCHASE_INQUIRY_CURRENT_STATE.fa.md edits were preserved.

## Deployment
No server deployment, actual SMS/channel send or release archive rebuild. This is developer tooling only.
