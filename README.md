# AI Commit Picker

AI Commit Picker is a terminal file selector that stages exactly the changes you choose, asks
a configurable provider for a commit message, and creates the Git commit locally. Codex and Claude
Code are included, and any command that follows the provider contract can be added without changing
the application.

## How it works

1. Reads `git status --porcelain` in the current repository.
2. Opens a full-screen picker with staged files selected by default.
3. Updates the Git index to match the selection.
4. Reads the staged diff and recent commit style, then sends that context to the selected provider.
5. Creates the commit locally and adds the provider's optional co-author footer.

The tool never pushes. The selected provider receives the prepared Git context from a temporary
working directory without write access to the repository; the Python process performs the final
`git commit` itself.

## Requirements

- Python 3.10 or newer
- Git
- At least one provider installed and authenticated. Built-in profiles are available for:
  - [OpenAI Codex CLI](https://developers.openai.com/codex/cli)
  - [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview)

## Install

```bash
git clone https://github.com/jpaniagua-dev/ai-commit-picker.git
cd ai-commit-picker
python -m pip install -e .
```

This installs the `ai-commit-picker` command. A short Git Bash alias is optional:

```bash
alias commit='ai-commit-picker'
```

## Use

Run the command inside any Git repository with local changes:

```bash
ai-commit-picker
```

Codex is selected by default. You can start with a specific provider or inspect the registry:

```bash
ai-commit-picker --provider claude
ai-commit-picker --provider codex
ai-commit-picker --list-providers
```

Keys:

- `Up` / `Down` or `k` / `j`: move
- `Space`: toggle one file
- `a`: toggle all files
- `t`: cycle through configured providers
- `Enter`: stage the selection and continue
- `q`, `Esc`, or `Ctrl+C`: cancel

Built-in provider configurations:

| Provider | Model | Effort | Session safeguards |
| --- | --- | --- | --- |
| Codex (default) | GPT-5.6 Terra | Low | Ephemeral, temporary working directory, read-only sandbox, no approvals |
| Claude Code | Sonnet | Low | No persistence, safe mode, no tools or permission prompts |

## Custom providers

A provider is any non-interactive command that:

1. reads the complete prompt from standard input;
2. writes only the commit message to standard output;
3. exits with status zero on success.

Create `config.toml` in one of these locations:

- Windows: `%APPDATA%\ai-commit-picker\config.toml`
- Linux and macOS: `${XDG_CONFIG_HOME:-~/.config}/ai-commit-picker/config.toml`

The `AI_COMMIT_PICKER_CONFIG` environment variable or `--config PATH` can select another file.

```toml
default_provider = "local"

[providers.local]
label = "Local model"
command = ["my-commit-provider", "--quiet"]
model = "example-model"
effort = "low"
timeout = 120
footer = "Co-Authored-By: Local Model <noreply@example.com>"
```

`label`, `model`, `effort`, `timeout`, and `footer` are optional. The default timeout is 120 seconds,
and omitting `footer` creates the commit without a co-author footer. A small wrapper script can adapt
a CLI that does not natively use stdin for its prompt or stdout for its response. Custom provider IDs
must not replace the built-in `codex` or `claude` profiles; use a distinct ID for customized commands.

Commands are argument arrays, not shell strings. AI Commit Picker never invokes them through a
shell. Do not place API keys or other secrets in the command array; use the provider's normal
authentication mechanism instead.

## Privacy and safety

The selected staged diff and recent Git history are sent to the selected provider so it can write
the message. Do not use this tool on content that the provider is not allowed to process.

No API key, agent authentication file, repository content, path, or commit diff is stored in this
project. Authentication remains in the user's existing CLI configuration. Custom providers are
trusted local commands and may not offer the same read-only or tool-free guarantees as the built-in
profiles. Normal Git hooks still run during `git commit` and may affect the working tree according
to the repository's own configuration.

## Test

```bash
python -m unittest discover -s tests
```

## License

MIT
