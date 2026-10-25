# Shared engineering workflow

Applies to Claude Code and Codex. User instructions and host permissions take precedence. Communicate in Persian; keep identifiers stable.

## Source of truth
- Backend OpenSpec remains authoritative: openspec/project.md, openspec/specs/ and active openspec/changes/.
- BMAD planning outputs live in docs/engineering/bmad-output/. Its spec folders contain SPEC.md, append-only .memlog.md and companions. Update the memlog through the spec workflow rather than hand-editing a derived SPEC.
- Link each BMAD feature spec to its OpenSpec change ID. Frontend plans reference the same change and API contract. Resolve disagreements explicitly.
- Skills: .agents/skills/ for Codex and .claude/skills/ for Claude Code. Keep both copies identical. The entrypoint is kaveh-engineering.

## Workflow
1. Inspect code, migrations, APIs, tests, active plans and working tree. Distinguish verified behavior from proposals; cite paths.
2. For substantial new work, use BMAD for product brief/PRD, UX, architecture and spec as needed. Define business rules, actors, permissions, acceptance scenarios and API contracts before implementation. Small maintenance does not need a full ERP design ceremony.
3. Include Mermaid flowchart, ERD, class and sequence diagrams where useful. Label CURRENT versus PROPOSED. Use actual entity names for current diagrams; document transactions and invariants too.
4. Design user flows, Persian/RTL copy, loading/empty/error/success states, mobile layouts, keyboard navigation and design tokens. Use frontend-design for visual implementation within the existing brand. Inspect screenshots.
5. Present a concrete design when review is needed. Previously approved designs and explicit implementation authorization remain valid; do not ask for identical approval again. Ask for material missing business decisions.
6. Choose ONE implementation coordinator: bmad-build OR Superpowers writing-plans followed by subagent-driven-development/executing-plans. Do not nest coordinators or restart brainstorming for an accepted BMAD spec.
7. Test behavior changes meaningfully, reproduce defects, implement and verify. Separate spec-compliance review from code/security review. Use subagents only when supported and authorized by user/host; otherwise review sequentially and disclose that limitation.
8. Record actual commands and results. Mock provider sends. Installation of this workflow is not permission to send real SMS/channel messages, deploy or publish; existing explicit authorization for an action still applies.
9. Update tasks, handoff and decisions. Never equate local tests with deployment or provider delivery. Preserve unrelated changes and secrets.

## Handoff
Before switching tools, write docs/engineering/HANDOFF.md using the template. Include objective, accepted decisions, spec/change links, files, checks, unresolved issues and next action. The next tool reads it and verifies the working tree.

## Installation and updates
toolchain-lock.json records versions and commits. BMAD uses its pinned official installer for codex,claude-code. Superpowers and frontend-design are project-local skills, not marketplace registrations; no SessionStart plugin hook was installed. AGENTS.md/CLAUDE.md route assistants to this workflow. Reopen the coding session after installation.

Plain ChatGPT web cannot discover local folders: attach the spec, diagrams and handoff there, or use Codex with this workspace. Claude Code still requires a separately installed/authenticated Claude client.

Update deliberately: inspect upstream changes, reinstall pinned sources, synchronize both trees and run the verifier. Preserve project instructions and custom BMAD configuration.

Project-local Superpowers skills use their bare names; resolve upstream superpowers:<name> references to .agents/skills/<name>/SKILL.md (Codex) or .claude/skills/<name>/SKILL.md (Claude). This is a local-skill installation, not a namespaced plugin.
