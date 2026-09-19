import unittest
from types import SimpleNamespace
from unittest.mock import patch

import ai_commit_picker


class CategorizeTests(unittest.TestCase):
    def test_untracked_file_is_not_staged(self):
        self.assertEqual(('untracked', False), ai_commit_picker.categorize('??'))

    def test_index_change_is_staged(self):
        self.assertEqual(('staged', True), ai_commit_picker.categorize('M '))

    def test_deleted_file_keeps_staged_state(self):
        self.assertEqual(('deleted', True), ai_commit_picker.categorize('D '))


class CodexTests(unittest.TestCase):
    def test_command_uses_read_only_ephemeral_session(self):
        command = ai_commit_picker.codex_command()

        self.assertIn('--ephemeral', command)
        self.assertEqual('gpt-5.6-terra', command[command.index('--model') + 1])
        self.assertEqual('read-only', command[command.index('--sandbox') + 1])
        self.assertNotIn('workspace-write', command)

    @patch('ai_commit_picker.subprocess.run')
    def test_message_is_read_from_codex_stdout(self, run):
        run.return_value = SimpleNamespace(returncode=0, stdout='Add focused tests\n')

        message, code = ai_commit_picker.generate_commit_message()

        self.assertEqual(0, code)
        self.assertEqual('Add focused tests', message)

    @patch('ai_commit_picker.subprocess.run')
    def test_commit_adds_codex_footer(self, run):
        run.return_value = SimpleNamespace(returncode=0)

        code = ai_commit_picker.create_commit('Add focused tests')

        self.assertEqual(0, code)
        self.assertEqual(['git', 'commit', '-F', '-'], run.call_args.args[0])
        self.assertIn(ai_commit_picker.COAUTHOR_FOOTER, run.call_args.kwargs['input'])


if __name__ == '__main__':
    unittest.main()
