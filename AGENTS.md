# Repository instructions

This is a public repository. Keep source, fixtures, documentation, and history free of real
repository paths, client names, issue keys, credentials, tokens, and private commit content.

- Write code, comments, documentation, and commit messages in English.
- Preserve the security boundary: the selected agent receives prepared Git context from a temporary
  working directory without repository write access. Claude has no tools; Codex uses its read-only
  sandbox. Only the Python process may change the index or create the commit.
- Never add push behavior.
- Run `python -m unittest discover -s tests` after changing Python code.
