# Current local engineering runner architecture

Source: `tools/engineering_flow/workflow.py`, `flow.py` and `tools/engineering.ps1`. These diagrams describe the local implementation, not the marketplace or a proposed distributed agent platform.

## Component responsibilities

```mermaid
classDiagram
  class Runner {
    database: Path
    lock: Path
    graph: CompiledStateGraph
    start(task, objective, repositories)
    status(task)
    submit(task, checkpoint, actor, artifacts)
    approve(task, checkpoint, actor, evidence)
    revise(task, checkpoint, stage, actor, reason)
  }
  class State {
    schema_version: int
    objective: str
    repositories: dict
    records: dict
    history: list
    phase: str
  }
  class CompiledStateGraph
  class SqliteSaver
  class WorkflowError
  Runner --> CompiledStateGraph : invokes and resumes
  CompiledStateGraph --> State : persists typed state
  CompiledStateGraph --> SqliteSaver : checkpoints
  Runner ..> WorkflowError : rejects invalid operations
```

`records` contains current stage receipts, while `history` retains accepted receipts and revision/rejection events. Artifact references contain a registered repository alias, relative path and SHA256, not file contents. SQLite stores LangGraph checkpoints; there is no new Django model or application migration.

## Work and approval sequence

```mermaid
sequenceDiagram
  actor Owner
  participant Assistant as Claude Code or Codex
  participant CLI as Shared local CLI
  participant Graph as LangGraph
  participant DB as SQLite checkpoint store
  Assistant->>CLI: status(task)
  CLI->>Graph: get_state(thread_id)
  Graph->>DB: load checkpoint
  CLI-->>Assistant: stage, instructions, checkpoint token
  Assistant->>Assistant: perform the stage and write evidence files
  Assistant->>CLI: submit(token, artifact paths)
  CLI->>CLI: validate token, paths and upstream hashes
  CLI->>Graph: Command(resume=receipt)
  Graph->>DB: persist next interrupt and current state
  CLI-->>Assistant: next stage or human approval gate
  Assistant->>Owner: present concrete artifacts for decision
  Owner-->>Assistant: explicit approval or rejection
  Assistant->>CLI: approve/reject(token, decision evidence)
  CLI->>Graph: resume validated decision receipt
  Graph->>DB: persist transition and history
```

The local CLI does not independently authenticate the owner or verify reported test success. Host instructions govern whether the assistant may record approval or execute actions. An external multi-user service would require additional identity, authorization, isolation and persistence design.

## Failure/revision behavior

- Stale checkpoint: reject the request; read current status.
- Changed upstream artifact: refuse advancement; revise the earliest affected stage.
- Design rejection: return to architecture; discard current downstream records/approvals.
- Implementation-plan rejection: return to planning.
- Failed spec or quality review: return to implementation; both review perspectives run again.
- Concurrent process: fail on the exclusive local lock; do not mutate the graph.
- Process restart: reopen the same task in the shared SQLite store.
- Crash leaving a lock file: operator verifies no process remains before removing only the lock file. No automatic lock stealing.
