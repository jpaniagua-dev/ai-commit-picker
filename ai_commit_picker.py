#!/usr/bin/env python
import sys
import subprocess

from prompt_toolkit.application import Application
from prompt_toolkit.data_structures import Point
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style


CATEGORY_ORDER = [
    ('staged',    'Staged'),
    ('modified',  'Modified'),
    ('deleted',   'Deleted'),
    ('untracked', 'Untracked'),
]


CODEX_PROMPT = """\
Write a git commit message for the currently staged files.

Steps:
1. Run `git log --oneline -10` to learn the project's commit style.
2. Run `git diff --cached` to read the staged changes.
3. Generate a concise subject and, only when useful, a short body matching the project style.

Return only the commit message, without code fences, commentary, or a co-author footer.
Do not run `git commit`, push, modify files, or change the index.
"""

CODEX_MODEL = 'gpt-5.6-terra'
CODEX_REASONING_EFFORT = 'low'
COAUTHOR_FOOTER = 'Co-Authored-By: Codex <noreply@openai.com>'


TUI_STYLE = Style.from_dict({
    'title':    'bold #ffffff bg:#005f87',
    'header':   'bold #d7af00',
    'selected': 'reverse bold',
    'checked':  '#5fd75f',
    'hint':     '#888888',
    'count':    'bold #87afff',
})


def is_git_repo():
    try:
        subprocess.run(
            ['git', 'rev-parse', '--is-inside-work-tree'],
            capture_output=True, check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def categorize(code):
    """Return (category, is_staged) from a 2-char porcelain code."""
    if code == '??':
        return ('untracked', False)
    x, y = code[0], code[1]
    staged = x not in (' ', '?')
    if 'D' in (x, y):
        return ('deleted', staged)
    if staged and y == ' ':
        return ('staged', True)
    return ('modified', staged)


def parse_porcelain():
    """Run `git status --porcelain` and return a list of file dicts."""
    result = subprocess.run(
        ['git', 'status', '--porcelain'],
        capture_output=True, text=True, check=True,
    )
    files = []
    for line in result.stdout.splitlines():
        if len(line) < 3:
            continue
        code = line[:2]
        path = line[3:]
        if ' -> ' in path:
            path = path.split(' -> ', 1)[1]
        category, staged = categorize(code)
        files.append({
            'path': path,
            'category': category,
            'staged': staged,
            'checked': staged,
        })
    return files


def order_files(files):
    """Group files by category in display order, returning a list of header/file rows."""
    grouped = {key: [] for key, _ in CATEGORY_ORDER}
    for f in files:
        grouped.setdefault(f['category'], []).append(f)
    rows = []
    for key, label in CATEGORY_ORDER:
        bucket = grouped.get(key, [])
        if not bucket:
            continue
        rows.append({'type': 'header', 'label': label})
        for f in bucket:
            rows.append({'type': 'file', 'file': f})
    return rows


class FilePicker:
    """Multi-select TUI: checkboxes over `git status` files, Enter to confirm."""

    def __init__(self, files):
        self.files = files
        self.rows = order_files(files)
        self.file_positions = [i for i, r in enumerate(self.rows) if r['type'] == 'file']
        self.cursor = 0
        self._cursor_y = 0
        self.result = None  # None = cancelled; list = selected files

    def _render(self):
        fragments = [
            ('class:title', " AI Commit Picker "),
            ('', '\n\n'),
        ]
        line_count = 2  # title + blank line

        if not self.file_positions:
            fragments.append(('class:hint', "  No changes to commit.\n"))

        selected_row_idx = (
            self.file_positions[self.cursor] if self.file_positions else -1
        )

        for i, row in enumerate(self.rows):
            if row['type'] == 'header':
                fragments.append(('', '\n'))
                fragments.append(('class:header', f"  {row['label']}\n"))
                line_count += 2
                continue

            f = row['file']
            is_selected = (i == selected_row_idx)
            if is_selected:
                self._cursor_y = line_count
            prefix = '> ' if is_selected else '  '
            checkbox = '[x]' if f['checked'] else '[ ]'
            if is_selected:
                line_style = 'class:selected'
            elif f['checked']:
                line_style = 'class:checked'
            else:
                line_style = ''
            fragments.append((line_style, f"{prefix}{checkbox}  {f['path']}\n"))
            line_count += 1

        checked_count = sum(1 for f in self.files if f['checked'])
        fragments.append(('', '\n'))
        fragments.append(('class:count', f"  {checked_count} selected"))
        fragments.append((
            'class:hint',
            "\n  space: toggle   a: toggle all   enter: commit   q/esc: cancel\n",
        ))
        return FormattedText(fragments)

    def _toggle_current(self):
        if not self.file_positions:
            return
        f = self.rows[self.file_positions[self.cursor]]['file']
        f['checked'] = not f['checked']

    def _toggle_all(self):
        any_unchecked = any(not f['checked'] for f in self.files)
        for f in self.files:
            f['checked'] = any_unchecked

    def run(self):
        kb = KeyBindings()

        @kb.add('up')
        @kb.add('k')
        def _(event):
            if self.cursor > 0:
                self.cursor -= 1

        @kb.add('down')
        @kb.add('j')
        def _(event):
            if self.cursor < len(self.file_positions) - 1:
                self.cursor += 1

        @kb.add('home')
        @kb.add('g')
        def _(event):
            self.cursor = 0

        @kb.add('end')
        @kb.add('G')
        def _(event):
            if self.file_positions:
                self.cursor = len(self.file_positions) - 1

        @kb.add('space')
        def _(event):
            self._toggle_current()

        @kb.add('a')
        def _(event):
            self._toggle_all()

        @kb.add('enter')
        def _(event):
            self.result = [f for f in self.files if f['checked']]
            event.app.exit()

        @kb.add('q')
        @kb.add('escape')
        @kb.add('c-c')
        def _(event):
            self.result = None
            event.app.exit()

        control = FormattedTextControl(
            self._render,
            focusable=True,
            show_cursor=False,
            get_cursor_position=lambda: Point(x=0, y=self._cursor_y),
        )
        layout = Layout(HSplit([Window(content=control, wrap_lines=False)]))
        app = Application(
            layout=layout,
            key_bindings=kb,
            full_screen=True,
            style=TUI_STYLE,
        )
        app.run()
        return self.result


def sync_index(files):
    """Adjust the git index so it matches the user's checkbox selection."""
    for f in files:
        path = f['path']
        if f['checked']:
            subprocess.run(['git', 'add', '--', path], check=True)
        elif f['staged']:
            subprocess.run(
                ['git', 'reset', 'HEAD', '--', path],
                check=True, capture_output=True,
            )


def index_has_changes():
    """Return True if there is anything staged."""
    result = subprocess.run(['git', 'diff', '--cached', '--quiet'], check=False)
    return result.returncode != 0


def codex_command():
    """Return the read-only Codex command used to generate a commit message."""
    return [
        'codex',
        '--ask-for-approval', 'never',
        'exec',
        '--ephemeral',
        '--model', CODEX_MODEL,
        '--config', f'model_reasoning_effort="{CODEX_REASONING_EFFORT}"',
        '--sandbox', 'read-only',
        '--color', 'never',
        CODEX_PROMPT,
    ]


def generate_commit_message():
    """Ask Codex for a commit message without granting write access."""
    try:
        result = subprocess.run(
            codex_command(),
            check=False,
            stdout=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        print("Error: `codex` CLI not found in PATH.")
        return None, 1

    if result.returncode != 0:
        print(f"Error: Codex exited with status {result.returncode}.")
        return None, result.returncode

    message = result.stdout.strip()
    if not message:
        print("Error: Codex returned an empty commit message.")
        return None, 1

    return message, 0


def create_commit(message):
    """Create the commit from a validated message and fixed attribution footer."""
    commit_message = f"{message.rstrip()}\n\n{COAUTHOR_FOOTER}\n"
    result = subprocess.run(
        ['git', 'commit', '-F', '-'],
        input=commit_message,
        text=True,
        check=False,
    )
    return result.returncode


def main():
    print("###########################################")
    print("AI Commit Picker")
    print("###########################################")

    if not is_git_repo():
        print("Error: not a git repository.")
        sys.exit(1)

    files = parse_porcelain()
    if not files:
        print("Nothing to commit (working tree clean).")
        return

    picker = FilePicker(files)
    selection = picker.run()

    if selection is None:
        print("Cancelled.")
        return
    if not selection:
        print("No files selected. Nothing to commit.")
        return

    print(f"Staging {len(selection)} file(s)...")
    sync_index(files)

    if not index_has_changes():
        print("Index is empty after sync. Nothing to commit.")
        return

    print(f"Generating a commit message with {CODEX_MODEL} ({CODEX_REASONING_EFFORT} reasoning)...\n")
    message, code = generate_commit_message()
    if code != 0:
        sys.exit(code)

    print("\nCreating commit...")
    sys.exit(create_commit(message))


if __name__ == "__main__":
    main()
