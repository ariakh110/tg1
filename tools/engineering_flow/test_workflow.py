import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from workflow import Runner, WorkflowError, STAGES


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.db = self.root / 'state.sqlite3'

    def tearDown(self):
        self.temp.cleanup()

    def start(self, task='sample'):
        with Runner(self.db) as runner:
            return runner.start(task, 'Review a feature', {'backend': str(self.repo)})

    def artifact(self, name='report.md'):
        p = self.repo / name
        p.write_text('# Verified evidence\n', encoding='utf-8')
        return {'repo': 'backend', 'path': name}

    def submit(self, task, status, **extra):
        with Runner(self.db) as runner:
            return runner.submit(task, checkpoint=status['checkpoint'], actor='codex',
                                 artifacts=[self.artifact(status['stage'] + '.md')], **extra)

    def advance_to(self, target):
        status = self.start()
        while status['stage'] != target:
            status = self.submit('sample', status)
        return status

    def test_restart_preserves_pending_stage_and_prevents_duplicate_start(self):
        status = self.start()
        self.assertEqual(status['stage'], 'context')
        with Runner(self.db) as runner:
            self.assertEqual(runner.status('sample')['checkpoint'], status['checkpoint'])
            with self.assertRaises(WorkflowError):
                runner.start('sample', 'Overwrite', {'backend': str(self.repo)})
        next_status = self.submit('sample', status)
        self.assertEqual(next_status['stage'], 'prd')
        with self.assertRaises(WorkflowError):
            self.submit('sample', status)

    def test_all_stages_require_artifacts_and_approval_is_separate(self):
        status = self.advance_to('design_approval')
        with self.assertRaises(WorkflowError):
            self.submit('sample', status)
        with Runner(self.db) as runner:
            with self.assertRaises(WorkflowError):
                runner.approve('sample', checkpoint=status['checkpoint'], actor='Aria', evidence='')
            status = runner.approve('sample', checkpoint=status['checkpoint'], actor='Aria', evidence='User approved the linked design')
        self.assertEqual(status['stage'], 'plan')

    def test_empty_receipt_cannot_advance_and_runtime_makes_no_network_call(self):
        from langsmith import tracing_context
        with tracing_context(enabled=True), patch('socket.socket.connect') as connect:
            status = self.start()
            with Runner(self.db) as runner:
                with self.assertRaises(WorkflowError):
                    runner.submit('sample', checkpoint=status['checkpoint'], actor='codex', artifacts=[])
                self.assertEqual(runner.status('sample')['stage'], 'context')
            connect.assert_not_called()

    def test_changed_artifact_cannot_be_approved(self):
        status = self.advance_to('design_approval')
        (self.repo / 'architecture.md').write_text('Changed after review', encoding='utf-8')
        with Runner(self.db) as runner:
            with self.assertRaises(WorkflowError):
                runner.approve('sample', checkpoint=status['checkpoint'], actor='Aria', evidence='Approved')
            self.assertEqual(runner.status('sample')['stage'], 'design_approval')

    def test_path_escape_secret_and_empty_file_are_rejected(self):
        status = self.start()
        for name in ['../outside.md', '.env', 'empty.md']:
            (self.repo / name).write_text('' if name == 'empty.md' else 'secret', encoding='utf-8')
            with Runner(self.db) as runner:
                with self.assertRaises(WorkflowError):
                    runner.submit('sample', checkpoint=status['checkpoint'], actor='codex', artifacts=[{'repo': 'backend', 'path': name}])
        self.assertEqual(self.submit('sample', status)['stage'], 'prd')

    def test_complete_flow_accepts_both_executors_and_review_failure_reworks(self):
        status = self.start()
        seen = []
        failed = False
        while not status['finished']:
            seen.append(status['stage'])
            with Runner(self.db) as runner:
                if status['stage'].endswith('_approval'):
                    status = runner.approve('sample', checkpoint=status['checkpoint'], actor='Aria', evidence='Explicit approval in test')
                else:
                    outcome = 'fail' if status['stage'] == 'spec_review' and not failed else 'pass'
                    failed |= outcome == 'fail'
                    status = runner.submit('sample', checkpoint=status['checkpoint'], actor='claude', outcome=outcome,
                                           artifacts=[self.artifact(status['stage'] + '.md')])
        self.assertEqual(status['stage'], 'ready_for_handoff')
        self.assertEqual(seen.count('implementation'), 2)
        self.assertTrue(set(STAGES).issubset(seen))
        with Runner(self.db) as runner:
            self.assertTrue(runner.status('sample')['finished'])

    def test_rejected_design_returns_to_architecture_and_invalidates_downstream(self):
        status = self.advance_to('design_approval')
        with Runner(self.db) as runner:
            status = runner.approve('sample', checkpoint=status['checkpoint'], actor='Aria', evidence='Revise the design', reject=True)
        self.assertEqual(status['stage'], 'architecture')
        self.assertNotIn('spec', status['records'])

    def test_unknown_task_and_concurrent_writer_fail_explicitly(self):
        with Runner(self.db) as runner:
            with self.assertRaises(WorkflowError):
                runner.status('missing')
            with self.assertRaises(WorkflowError):
                with Runner(self.db):
                    pass

    def test_revision_reopens_changed_design_and_discards_approvals(self):
        status = self.advance_to('design_approval')
        with Runner(self.db) as runner:
            status = runner.approve('sample', checkpoint=status['checkpoint'], actor='Aria', evidence='Approved design')
        (self.repo / 'architecture.md').write_text('New design', encoding='utf-8')
        with Runner(self.db) as runner:
            with self.assertRaises(WorkflowError):
                runner.revise('sample', checkpoint=status['checkpoint'], actor='codex', stage='implementation', reason='Skip ahead')
            status = runner.revise('sample', checkpoint=status['checkpoint'], actor='codex', stage='architecture', reason='Design changed')
        self.assertEqual(status['stage'], 'architecture')
        self.assertNotIn('design_approval', status['records'])
        self.assertEqual(status['history'][-1]['outcome'], 'revise')


if __name__ == '__main__':
    unittest.main()
