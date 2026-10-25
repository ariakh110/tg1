<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->
## Shared AI engineering workflow
For engineering work, read docs/engineering/WORKFLOW.md and docs/engineering/PROJECT_CONTEXT.md; read docs/engineering/HANDOFF.md when present. Use the project-local kaveh-engineering skill to route BMAD planning/architecture/UX and one implementation coordinator. Preserve existing OpenSpec requirements. User instructions and host permissions take precedence. Skills are in .agents/skills/ (Codex) and .claude/skills/ (Claude Code). Do not duplicate approved planning.
