# Engineering handoff: toolchain installation

## Objective/status
Install a shared Claude Code / Codex engineering workflow. Completed locally on 2026-10-25.

## Accepted decisions
User requested execution for both tools. Existing backend OpenSpec retained. BMAD 6.12.4 stable; Superpowers 7.0.1 pinned; official frontend-design pinned. Project-local skills, no plugin hooks. One implementation coordinator per item.

## Files
See toolchain-lock.json, AGENTS.md, CLAUDE.md, WORKFLOW.md, PROJECT_CONTEXT.md, START.fa.md. Both discovery directories contain 46 skills and 300 identical files. Personal BMAD configuration/rendered caches remain ignored.

## Verification
verify_toolchain.py --runtime passed in both repositories. uv 0.13.5 installed from official GitHub release and archive SHA256 verified. BMAD build workflow rendering succeeded for the Codex backend and Claude frontend paths. This validates files/config/runtime, not a live Claude session: Claude executable is not on the current PATH.

## Next action
Start a fresh Codex/Claude Code session at an application repository root, invoke kaveh-engineering, then select the feature to analyze. The learner workspace also has a launcher to locate both repositories. Restart the terminal if uv is not discovered on its old PATH.

## Product/deployment
No product behavior, runtime dependency, database schema or server deployment changed. No real provider messages sent. Existing release bundles were not rebuilt for development-only tooling.
