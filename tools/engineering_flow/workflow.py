"""Local, operator-driven LangGraph workflow. Never executes model or shell calls."""
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import sqlite3
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from langsmith import tracing_context


STAGES = ('context', 'prd', 'architecture', 'ux', 'spec', 'design_approval',
          'plan', 'implementation_approval', 'implementation', 'spec_review',
          'quality_review', 'handoff')
GATES = {'design_approval', 'implementation_approval'}
REVIEWS = {'spec_review', 'quality_review'}
NEXT = dict(zip(STAGES, (*STAGES[1:], 'ready_for_handoff')))
SKILLS = {
    'context': 'bmad-project-context', 'prd': 'bmad-prd',
    'architecture': 'bmad-architecture; flowchart, ERD, class and sequence diagrams as needed',
    'ux': 'bmad-ux; frontend-design for visual implementation', 'spec': 'bmad-spec; link OpenSpec change',
    'plan': 'writing-plans', 'implementation': 'test-driven-development; approved plan',
    'spec_review': 'review against accepted spec', 'quality_review': 'bmad-review; security and test evidence',
    'handoff': 'verification-before-completion; record actual deployment status',
}


class WorkflowError(ValueError):
    """A recoverable operator error; pending work remains unchanged."""


class State(TypedDict):
    schema_version: int
    objective: str
    repositories: dict[str, str]
    records: dict
    history: list
    phase: str


def now():
    return datetime.now(timezone.utc).isoformat()


def text(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 4000:
        raise WorkflowError(f'{label} must be nonempty text, at most 4000 characters')
    return value.strip()


def file_record(repositories, item):
    if not isinstance(item, dict) or item.get('repo') not in repositories:
        raise WorkflowError('Artifact needs a registered repo and relative path')
    relative = item.get('path', '')
    if not isinstance(relative, str) or not relative:
        raise WorkflowError('Artifact path is required')
    relative = Path(relative.replace('\\', '/'))
    root = Path(repositories[item['repo']]).resolve()
    path = (root / relative).resolve()
    if relative.is_absolute() or not path.is_relative_to(root):
        raise WorkflowError('Artifact must remain inside its registered repository')
    parts = [part.lower() for part in path.relative_to(root).parts]
    forbidden = {'.git', '.venv', 'node_modules', '.engineering-state'}
    if any(part in forbidden or part == '.env' or part.startswith('.env.') for part in parts):
        raise WorkflowError('Secret, runtime or dependency files cannot be artifacts')
    if path.suffix.lower() in {'.pem', '.key', '.p12', '.sqlite3', '.db'}:
        raise WorkflowError('Private keys and database files cannot be artifacts')
    if not path.is_file() or not 0 < path.stat().st_size <= 10 * 1024 * 1024:
        raise WorkflowError('Artifact must be a nonempty file no larger than 10 MiB')
    return {'repo': item['repo'], 'path': path.relative_to(root).as_posix(),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def verify_records(state):
    for record in state['records'].values():
        for item in record.get('artifacts', []):
            if file_record(state['repositories'], item)['sha256'] != item['sha256']:
                raise WorkflowError(f'Artifact changed after submission: {item["repo"]}:{item["path"]}. '
                                    'Reject/revise the affected stage or create a linked replacement task.')


def graph_for(checkpointer):
    builder = StateGraph(State)

    def make_node(stage):
        def node(state):
            # Everything before interrupt is pure. Resuming may replay this code.
            receipt = interrupt({'stage': stage, 'kind': 'human_approval' if stage in GATES else 'work',
                                 'objective': state['objective'], 'guidance': SKILLS.get(stage, 'Human reviews the linked artifacts'),
                                 'artifacts_to_review': state['records']})
            records = dict(state['records'])
            if receipt['outcome'] == 'revise':
                target = receipt['target']
            elif receipt['outcome'] == 'reject':
                target = 'architecture' if stage == 'design_approval' else 'plan'
            elif receipt['outcome'] == 'fail':
                target = 'implementation'
            else:
                target = NEXT[stage]
            if target in STAGES and STAGES.index(target) <= STAGES.index(stage):
                for key in STAGES[STAGES.index(target):]:
                    records.pop(key, None)
            else:
                records[stage] = receipt
            history = [*state['history'], {'stage': stage, **receipt}]
            return Command(update={'records': records, 'history': history, 'phase': target},
                           goto=END if target == 'ready_for_handoff' else target)
        return node

    for stage in STAGES:
        builder.add_node(stage, make_node(stage))
    builder.add_edge(START, STAGES[0])
    return builder.compile(checkpointer=checkpointer)


class Runner:
    def __init__(self, database):
        self.database = Path(database)
        self.lock = self.database.with_suffix(self.database.suffix + '.lock')

    def __enter__(self):
        self.database.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise WorkflowError('Another process owns the state lock. Retry after it finishes; '
                                'after a crash verify no runner remains before removing only this lock file.') from None
        os.close(fd)
        self.tracing = tracing_context(enabled=False)
        self.tracing.__enter__()
        try:
            self.connection = sqlite3.connect(self.database, check_same_thread=False)
            self.connection.execute('PRAGMA busy_timeout=5000')
            self.graph = graph_for(SqliteSaver(self.connection))
            return self
        except BaseException:
            if hasattr(self, 'connection'):
                self.connection.close()
            self.lock.unlink(missing_ok=True)
            self.tracing.__exit__(None, None, None)
            raise

    def __exit__(self, *exc):
        try:
            self.connection.close()
        finally:
            self.lock.unlink(missing_ok=True)
            self.tracing.__exit__(*exc)

    def config(self, task):
        if not isinstance(task, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', task):
            raise WorkflowError('Task ID must be 1-80 lowercase letters, digits or hyphens')
        return {'configurable': {'thread_id': task}}

    def snapshot(self, task):
        snapshot = self.graph.get_state(self.config(task))
        if not snapshot.values:
            raise WorkflowError('Unknown task; start it first')
        if snapshot.values.get('schema_version') != 1:
            raise WorkflowError('Unsupported persisted workflow schema; do not overwrite state')
        return snapshot

    def status(self, task):
        snapshot = self.snapshot(task)
        pending = [i.value for t in snapshot.tasks for i in t.interrupts]
        finished = not snapshot.next
        return {'status': 'success', 'task': task, 'summary': 'Workflow evidence complete' if finished else 'Awaiting stage receipt',
                'stage': pending[0]['stage'] if pending else snapshot.values['phase'],
                'finished': finished, 'checkpoint': snapshot.config['configurable']['checkpoint_id'],
                'pending': pending, 'records': snapshot.values['records'], 'history': snapshot.values['history'],
                'next_actions': [] if finished else ['Perform the pending stage in Claude Code or Codex; submit its artifacts or record explicit human approval'],
                'artifacts': [a for r in snapshot.values['records'].values() for a in r.get('artifacts', [])]}

    def start(self, task, objective, repositories):
        config = self.config(task)
        if self.graph.get_state(config).values:
            raise WorkflowError('Task already exists; resume its current checkpoint')
        if not isinstance(repositories, dict) or not repositories:
            raise WorkflowError('Register at least one repository')
        roots = {}
        for alias, directory in repositories.items():
            if not re.fullmatch(r'[a-z][a-z0-9_-]{0,30}', alias):
                raise WorkflowError('Invalid repository alias')
            path = Path(directory).resolve()
            if not path.is_dir():
                raise WorkflowError('Registered repository directory does not exist')
            roots[alias] = str(path)
        self.graph.invoke({'schema_version': 1, 'objective': text(objective, 'Objective'),
                           'repositories': roots, 'records': {}, 'history': [], 'phase': STAGES[0]}, config)
        return self.status(task)

    def pending(self, task, checkpoint):
        status = self.status(task)
        if status['finished'] or not status['pending']:
            raise WorkflowError('Task has no pending interrupt')
        if checkpoint != status['checkpoint']:
            raise WorkflowError('Stale checkpoint; read status again before resuming')
        return status['stage'], self.snapshot(task).values

    def submit(self, task, *, checkpoint, actor, artifacts, outcome='pass'):
        stage, state = self.pending(task, checkpoint)
        if stage in GATES:
            raise WorkflowError('This is a human approval gate; use approve/reject with user evidence')
        if outcome not in ({'pass', 'fail'} if stage in REVIEWS else {'pass'}):
            raise WorkflowError('Only a review can fail; normal stages need a completed artifact receipt')
        if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= 50:
            raise WorkflowError('Submit 1-50 artifact references')
        verify_records(state)
        receipt = {'actor': text(actor, 'Executor/reviewer'), 'outcome': outcome, 'at': now(),
                   'artifacts': [file_record(state['repositories'], a) for a in artifacts]}
        self.graph.invoke(Command(resume=receipt), self.config(task))
        return self.status(task)

    def approve(self, task, *, checkpoint, actor, evidence, reject=False):
        stage, state = self.pending(task, checkpoint)
        if stage not in GATES:
            raise WorkflowError('Current stage is work, not a human approval gate')
        # Rejection must be possible even when the design has been edited.
        if not reject:
            verify_records(state)
        receipt = {'actor': text(actor, 'Human approver'), 'evidence': text(evidence, 'Explicit user approval/rejection evidence'),
                   'outcome': 'reject' if reject else 'approved', 'at': now(), 'artifacts': []}
        self.graph.invoke(Command(resume=receipt), self.config(task))
        return self.status(task)

    def revise(self, task, *, checkpoint, stage, actor, reason):
        current, state = self.pending(task, checkpoint)
        if stage not in SKILLS or stage == 'handoff' or STAGES.index(stage) > STAGES.index(current):
            raise WorkflowError('Revision must target a current or earlier work stage')
        retained = {key: value for key, value in state['records'].items() if STAGES.index(key) < STAGES.index(stage)}
        verify_records({**state, 'records': retained})
        receipt = {'actor': text(actor, 'Executor'), 'outcome': 'revise', 'target': stage,
                   'reason': text(reason, 'Revision reason'), 'at': now(), 'artifacts': []}
        self.graph.invoke(Command(resume=receipt), self.config(task))
        return self.status(task)
