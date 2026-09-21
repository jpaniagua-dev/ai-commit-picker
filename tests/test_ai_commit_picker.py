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


class FilePickerTests(unittest.TestCase):
    def test_agent_can_be_toggled(self):
        picker = ai_commit_picker.FilePicker([], agent='codex')

        picker._toggle_agent()

        self.assertEqual('claude', picker.agent)


class CommandLineTests(unittest.TestCase):
    def test_codex_is_the_default_agent(self):
        self.assertEqual('codex', ai_commit_picker.parse_args([]).agent)

    def test_claude_can_be_selected(self):
        self.assertEqual('claude', ai_commit_picker.parse_args(['--agent', 'claude']).agent)


class AgentTests(unittest.TestCase):
    def test_command_uses_read_only_ephemeral_session(self):
        command = ai_commit_picker.codex_command()

        self.assertIn('--ephemeral', command)
        self.assertEqual('gpt-5.6-terra', command[command.index('--model') + 1])
        self.assertEqual('read-only', command[command.index('--sandbox') + 1])
        self.assertNotIn('workspace-write', command)
        self.assertIn('--ignore-user-config', command)
        self.assertIn('--skip-git-repo-check', command)
        self.assertEqual('-', command[-1])

    def test_claude_command_disables_tools_and_persistence(self):
        command = ai_commit_picker.claude_command()

        self.assertEqual('sonnet', command[command.index('--model') + 1])
        self.assertIn('--no-session-persistence', command)
        self.assertIn('--safe-mode', command)
        self.assertEqual('', command[command.index('--tools') + 1])
        self.assertEqual('none', command[command.index('--permission-prompts') + 1])
        self.assertIn('Never request', command[command.index('--system-prompt') + 1])

    def test_agent_input_marks_repository_content_as_untrusted(self):
        prompt = ai_commit_picker.agent_input('STAGED DIFF\n+example')

        self.assertIn('BEGIN UNTRUSTED GIT CONTEXT', prompt)
        self.assertIn('STAGED DIFF\n+example', prompt)

    @patch('ai_commit_picker.subprocess.run')
    def test_message_is_read_from_agent_stdout(self, run):
        run.return_value = SimpleNamespace(returncode=0, stdout='Add focused tests\n')

        message, code = ai_commit_picker.generate_commit_message('claude', 'git context')

        self.assertEqual(0, code)
        self.assertEqual('Add focused tests', message)
        self.assertIn('git context', run.call_args.kwargs['input'])
        self.assertIn('ai-commit-picker-', run.call_args.kwargs['cwd'])

    @patch('ai_commit_picker.subprocess.run')
    def test_commit_adds_selected_agent_footer(self, run):
        run.return_value = SimpleNamespace(returncode=0)

        code = ai_commit_picker.create_commit('Add focused tests', 'claude')

        self.assertEqual(0, code)
        self.assertEqual(['git', 'commit', '-F', '-'], run.call_args.args[0])
        self.assertIn(ai_commit_picker.COAUTHOR_FOOTERS['claude'], run.call_args.kwargs['input'])

    @patch('ai_commit_picker.subprocess.run')
    def test_git_context_contains_log_and_diff(self, run):
        run.side_effect = [
            SimpleNamespace(returncode=0, stdout='abc123 Add feature\n'),
            SimpleNamespace(returncode=0, stdout='diff --git a/file b/file\n'),
        ]

        context = ai_commit_picker.read_git_context()

        self.assertIn('abc123 Add feature', context)
        self.assertIn('diff --git a/file b/file', context)


if __name__ == '__main__':
    unittest.main()
