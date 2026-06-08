# plog

A minimal interactive CLI for keeping a running progress log. Type an entry,
hit Enter, and it's appended — with a timestamp — to both a Markdown file and
a JSONL file. No dependencies beyond the Python standard library.

## Features

- Interactive prompt — stays open so you can log multiple entries in a row
- Each entry is timestamped and written to:
  - `progress-log.md` — a human-readable Markdown bullet list
  - `progress-log.jsonl` — a structured, machine-readable log (one JSON object per line)
- Optional comma-separated tags per entry
- Writes are flushed and `fsync`'d immediately, so nothing is lost on a crash
- The screen clears after each entry to keep the terminal free of clutter
- A full-screen to-do list mode for tracking and editing tasks interactively

## Requirements

- Python 3.9+

## Usage

```bash
python3 plog.py
```

You'll see a prompt:

```
> finished the onboarding flow
```

Press Enter to log it. The entry is appended to both output files right away.

To exit, type `exit` or `quit`, or press `Ctrl+C` / `Ctrl+D`.

### Tags

Append `-- tag1, tag2` to an entry to attach comma-separated tags:

```
> fixed parser bug -- bugfix, parser
```

This produces:

- Markdown: `- [2026-06-08 14:32:05] fixed parser bug (bugfix, parser)`
- JSONL: `{"timestamp": "2026-06-08T14:32:05", "entry": "fixed parser bug", "tags": ["bugfix", "parser"]}`

Entries without `--` are logged with an empty tags list.

## To-do list mode

```bash
python3 plog.py todo
```

Launches a full-screen, session-based to-do manager. Each session is its own
named list, stored as `todo_sessions/<name>.json` inside your output directory.

### Session picker

On startup you'll see a list of existing sessions plus a **"+ New session"**
option:

| Key | Action |
| --- | --- |
| `↑` / `↓` (or `k` / `j`) | Move the selection |
| `Enter` | Open the selected session |
| `n` | Jump straight to "+ New session" |
| `Esc` | Quit the program |

Selecting "+ New session" prompts you for a name and creates an empty list
under that name, then opens it for editing.

### Editing a session

| Key | Action |
| --- | --- |
| `↑` / `↓` (or `k` / `j`) | Move the selection |
| `a` | Add a new item |
| `e` | Edit the selected item's text |
| `d` | Delete the selected item |
| `Space` / `Enter` | Toggle the selected item as done/not done |
| `Tab` / `Shift+Tab` | Indent/outdent the selected item, for sub-tasks |
| `s` | Save the current list as a copy under a new name |
| `q` | Save and return to the session picker |

While adding, editing, or naming a session, press `Enter` to confirm or `Esc`
to cancel. Completed items are shown with a `✓` and shaded a darker gray to
indicate they're done.

### Sub-tasks

Press `Tab` to indent the selected item one level (turning it into a sub-task
of the item above it) and `Shift+Tab` to outdent it back out. Indentation is
stored per item and persists with the session.

### Timestamps

Each item records when it was created (`created_at`) and, once checked off,
when it was completed (`completed_at`); unchecking an item clears its
completion time.

Every change (add, edit, delete, toggle) is saved to disk immediately, so
nothing is lost even if you exit unexpectedly. Pressing `s` saves a snapshot
of the current list under a different name — handy for branching off a
checklist. If that name is already in use, you'll be asked to confirm before
it's overwritten.

## Output location

By default, log files are written to `~/progress-log/`. You can change this with:

- the `PLOG_DIR` environment variable:

  ```bash
  export PLOG_DIR=~/my-logs
  ```

- the `--dir` flag, which takes precedence:

  ```bash
  python3 plog.py --dir ./my-logs
  ```

## Setting up a shortcut

Add an alias to your shell config (e.g. `~/.zshrc` or `~/.bashrc`):

```bash
alias plog="python3 /path/to/plog/plog.py"
```

Reload your shell (`source ~/.zshrc`) and run `plog` from anywhere.

## License

MIT
