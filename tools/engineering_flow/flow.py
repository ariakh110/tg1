"""JSON CLI shared by the Claude Code and Codex project launchers."""
import argparse
import json
from pathlib import Path
import sys

from workflow import Runner, WorkflowError


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database', type=Path, default=Path(__file__).resolve().parents[2] / '.engineering-state/workflow.sqlite3')
    commands = p.add_subparsers(dest='command', required=True)
    start = commands.add_parser('start', help='Create a task; pauses at the context stage')
    start.add_argument('task')
    start.add_argument('--objective', required=True)
    start.add_argument('--repo', action='append', required=True, metavar='ALIAS=PATH')
    status = commands.add_parser('status', help='Read the pending stage and checkpoint token')
    status.add_argument('task')
    for name in ['submit', 'approve', 'reject', 'revise']:
        action = commands.add_parser(name)
        action.add_argument('task')
        action.add_argument('--checkpoint', required=True)
        action.add_argument('--by', required=True, dest='actor')
        if name == 'submit':
            action.add_argument('--artifact', action='append', required=True, metavar='ALIAS:RELATIVE_PATH')
            action.add_argument('--outcome', choices=['pass', 'fail'], default='pass')
        elif name == 'revise':
            action.add_argument('--stage', required=True)
            action.add_argument('--reason', required=True)
        else:
            action.add_argument('--evidence', required=True, help='Quote/reference of explicit human decision; never fabricate')
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        with Runner(args.database) as runner:
            if args.command == 'start':
                repositories = {}
                for item in args.repo:
                    alias, separator, directory = item.partition('=')
                    if not separator or alias in repositories:
                        raise WorkflowError('Use distinct --repo ALIAS=PATH entries')
                    repositories[alias] = directory
                result = runner.start(args.task, args.objective, repositories)
            elif args.command == 'status':
                result = runner.status(args.task)
            elif args.command == 'submit':
                artifacts = []
                for item in args.artifact:
                    alias, separator, relative = item.partition(':')
                    if not separator:
                        raise WorkflowError('Use --artifact ALIAS:RELATIVE_PATH')
                    artifacts.append({'repo': alias, 'path': relative})
                result = runner.submit(args.task, checkpoint=args.checkpoint, actor=args.actor, artifacts=artifacts, outcome=args.outcome)
            elif args.command == 'revise':
                result = runner.revise(args.task, checkpoint=args.checkpoint, actor=args.actor, stage=args.stage, reason=args.reason)
            else:
                result = runner.approve(args.task, checkpoint=args.checkpoint, actor=args.actor,
                                        evidence=args.evidence, reject=args.command == 'reject')
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (WorkflowError, OSError) as error:
        print(json.dumps({'status': 'error', 'summary': str(error), 'next_actions': [
            'Read status; fix the receipt, path or checkpoint. Use revise for changed upstream artifacts. Do not overwrite the state database.'
        ], 'artifacts': []}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
