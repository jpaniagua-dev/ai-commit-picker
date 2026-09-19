# Repository instructions

This is a public repository. Keep source, fixtures, documentation, and history free of real
repository paths, client names, issue keys, credentials, tokens, and private commit content.

- Write code, comments, documentation, and commit messages in English.
- Preserve the security boundary: Codex may inspect the repository through the read-only sandbox,
  but only the Python process may change the index or create the commit.
- Never add push behavior.
- Run `python -m unittest discover -s tests` after changing Python code.
