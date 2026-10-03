import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
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
    def test_provider_cycles_through_registry(self):
        providers = ai_commit_picker.builtin_providers()
        providers['custom'] = ai_commit_picker.Provider(
            id='custom', label='Custom', command=('custom-provider',),
        )
        picker = ai_commit_picker.FilePicker([], providers, provider='codex')

        picker._cycle_provider()
        self.assertEqual('claude', picker.provider)
        picker._cycle_provider()
        self.assertEqual('custom', picker.provider)
        picker._cycle_provider()

        self.assertEqual('codex', picker.provider)


class CommandLineTests(unittest.TestCase):
    def test_codex_is_the_default_provider(self):
        self.assertEqual('codex', ai_commit_picker.parse_args([]).provider)

    def test_provider_can_be_selected(self):
        self.assertEqual(
            'claude',
            ai_commit_picker.parse_args(['--provider', 'claude']).provider,
        )

    def test_agent_option_has_been_removed(self):
        with patch('sys.stderr'), self.assertRaises(SystemExit):
            ai_commit_picker.parse_args(['--agent', 'claude'])


class ProviderTests(unittest.TestCase):
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

    def test_provider_input_marks_repository_content_as_untrusted(self):
        prompt = ai_commit_picker.provider_input('STAGED DIFF\n+example')

        self.assertIn('BEGIN UNTRUSTED GIT CONTEXT', prompt)
        self.assertIn('STAGED DIFF\n+example', prompt)

    def test_custom_provider_contract_runs_as_a_real_subprocess(self):
        provider = ai_commit_picker.Provider(
            id='custom',
            label='Custom',
            command=(
                sys.executable,
                '-c',
                'import sys; sys.stdin.read(); print("Generate portable message")',
            ),
        )

        message, code = ai_commit_picker.generate_commit_message(provider, 'git context')

        self.assertEqual(0, code)
        self.assertEqual('Generate portable message', message)

    @patch('ai_commit_picker.subprocess.run')
    def test_message_is_read_from_provider_stdout(self, run):
        run.return_value = SimpleNamespace(returncode=0, stdout='Add focused tests\n')
        provider = ai_commit_picker.Provider(
            id='custom', label='Custom', command=('custom-provider',), timeout=30,
        )

        message, code = ai_commit_picker.generate_commit_message(provider, 'git context')

        self.assertEqual(0, code)
        self.assertEqual('Add focused tests', message)
        self.assertEqual(['custom-provider'], run.call_args.args[0])
        self.assertIn('git context', run.call_args.kwargs['input'])
        self.assertIn('ai-commit-picker-', run.call_args.kwargs['cwd'])
        self.assertEqual(30, run.call_args.kwargs['timeout'])

    @patch('ai_commit_picker.subprocess.run')
    def test_commit_adds_selected_provider_footer(self, run):
        run.return_value = SimpleNamespace(returncode=0)
        provider = ai_commit_picker.builtin_providers()['claude']

        code = ai_commit_picker.create_commit('Add focused tests', provider)

        self.assertEqual(0, code)
        self.assertEqual(['git', 'commit', '-F', '-'], run.call_args.args[0])
        self.assertIn(provider.footer, run.call_args.kwargs['input'])

    @patch('ai_commit_picker.subprocess.run')
    def test_commit_allows_provider_without_footer(self, run):
        run.return_value = SimpleNamespace(returncode=0)
        provider = ai_commit_picker.Provider(
            id='custom', label='Custom', command=('custom-provider',),
        )

        ai_commit_picker.create_commit('Add focused tests', provider)

        self.assertEqual('Add focused tests\n', run.call_args.kwargs['input'])

    @patch('ai_commit_picker.subprocess.run')
    def test_git_context_contains_log_and_diff(self, run):
        run.side_effect = [
            SimpleNamespace(returncode=0, stdout='abc123 Add feature\n'),
            SimpleNamespace(returncode=0, stdout='diff --git a/file b/file\n'),
        ]

        context = ai_commit_picker.read_git_context()

        self.assertIn('abc123 Add feature', context)
        self.assertIn('diff --git a/file b/file', context)


class ProviderConfigTests(unittest.TestCase):
    def test_custom_provider_and_default_are_loaded_from_toml(self):
        with TemporaryDirectory() as temporary_dir:
            config_path = Path(temporary_dir) / 'config.toml'
            config_path.write_text(
                """\
default_provider = "local"

[providers.local]
label = "Local model"
command = ["local-commit-provider", "--quiet"]
model = "example-model"
timeout = 45
""",
                encoding='utf-8',
            )

            providers, default_provider, loaded_path = ai_commit_picker.load_provider_settings(
                config_path
            )

        self.assertEqual('local', default_provider)
        self.assertEqual(config_path, loaded_path)
        self.assertEqual(('local-commit-provider', '--quiet'), providers['local'].command)
        self.assertEqual('example-model', providers['local'].model)
        self.assertEqual(45, providers['local'].timeout)
        self.assertIn('codex', providers)

    def test_unknown_default_provider_is_rejected(self):
        with TemporaryDirectory() as temporary_dir:
            config_path = Path(temporary_dir) / 'config.toml'
            config_path.write_text('default_provider = "missing"\n', encoding='utf-8')

            with self.assertRaises(ai_commit_picker.ProviderConfigError):
                ai_commit_picker.load_provider_settings(config_path)

    def test_provider_command_must_be_an_argument_array(self):
        with self.assertRaises(ai_commit_picker.ProviderConfigError):
            ai_commit_picker.provider_from_config(
                'unsafe',
                {'command': 'provider --with-a-shell-string'},
            )

    def test_unknown_provider_field_is_rejected(self):
        with self.assertRaises(ai_commit_picker.ProviderConfigError):
            ai_commit_picker.provider_from_config(
                'custom',
                {'command': ['custom-provider'], 'timout': 30},
            )

    def test_custom_provider_cannot_replace_builtin_safeguards(self):
        with TemporaryDirectory() as temporary_dir:
            config_path = Path(temporary_dir) / 'config.toml'
            config_path.write_text(
                '[providers.codex]\ncommand = ["other-command"]\n',
                encoding='utf-8',
            )

            with self.assertRaises(ai_commit_picker.ProviderConfigError):
                ai_commit_picker.load_provider_settings(config_path)


if __name__ == '__main__':
    unittest.main()
