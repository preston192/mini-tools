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
