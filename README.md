# AI Commit Picker

AI Commit Picker is a terminal file selector that stages exactly the changes you choose, asks
OpenAI Codex or Claude Code for a commit message, and creates the Git commit locally.

## How it works

1. Reads `git status --porcelain` in the current repository.
2. Opens a full-screen picker with staged files selected by default.
3. Updates the Git index to match the selection.
4. Reads the staged diff and recent commit style, then sends that context to the selected agent.
5. Creates the commit locally and adds the selected agent's co-author footer.

The tool never pushes. The selected agent receives the prepared Git context from a temporary
working directory without write access to the repository; the Python process performs the final
`git commit` itself.

## Requirements

- Python 3.10 or newer
- Git
- At least one supported agent installed and authenticated:
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

Codex is selected by default. You can start with a specific agent:

```bash
ai-commit-picker --agent claude
ai-commit-picker --agent codex
```

Keys:

- `Up` / `Down` or `k` / `j`: move
- `Space`: toggle one file
- `a`: toggle all files
- `t`: switch between Codex and Claude Code
- `Enter`: stage the selection and continue
- `q`, `Esc`, or `Ctrl+C`: cancel

Agent configurations:

| Agent | Model | Effort | Session safeguards |
| --- | --- | --- | --- |
| Codex (default) | GPT-5.6 Terra | Low | Ephemeral, temporary working directory, read-only sandbox, no approvals |
| Claude Code | Sonnet | Low | No persistence, safe mode, no tools or permission prompts |

## Privacy and safety

The selected staged diff and recent Git history are sent to the selected provider so it can write
the message. Do not use this tool on content that your OpenAI or Anthropic account is not allowed
to process.

No API key, agent authentication file, repository content, path, or commit diff is stored in this
project. Authentication remains in the user's existing CLI configuration. Normal Git hooks still
run during `git commit` and may affect the working tree according to the repository's own
configuration.

## Test

```bash
python -m unittest discover -s tests
```

## License

MIT
