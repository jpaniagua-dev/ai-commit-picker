# AI Commit Picker

AI Commit Picker is a terminal file selector that stages exactly the changes you choose, asks
OpenAI Codex for a commit message, and creates the Git commit locally.

## How it works

1. Reads `git status --porcelain` in the current repository.
2. Opens a full-screen picker with staged files selected by default.
3. Updates the Git index to match the selection.
4. Runs Codex in a read-only, ephemeral session to inspect the staged diff and recent commit style.
5. Creates the commit locally and adds a Codex co-author footer.

The tool never pushes. Codex is not granted write access; the Python process performs the final
`git commit` itself.

## Requirements

- Python 3.10 or newer
- Git
- [OpenAI Codex CLI](https://developers.openai.com/codex/cli) installed and authenticated

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

Keys:

- `Up` / `Down` or `k` / `j`: move
- `Space`: toggle one file
- `a`: toggle all files
- `Enter`: stage the selection and continue
- `q`, `Esc`, or `Ctrl+C`: cancel

The default agent configuration is GPT-5.6 Terra with low reasoning effort. The Codex session is
ephemeral, uses the read-only sandbox, and never asks for an approval because it cannot write.

## Privacy and safety

The selected staged diff and recent Git history are made available to Codex so it can write the
message. Do not use this tool on content that your OpenAI account is not allowed to process.

No API key, Codex authentication file, repository content, path, or commit diff is stored in this
project. Authentication remains in the user's existing Codex CLI configuration. Normal Git hooks
still run during `git commit` and may affect the working tree according to the repository's own
configuration.

## Test

```bash
python -m unittest discover -s tests
```

## License

MIT
