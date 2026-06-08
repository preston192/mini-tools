#!/usr/bin/env python3
"""Interactive progress logger: appends timestamped entries to a markdown and a JSONL file."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_DIR = Path(os.environ.get("PLOG_DIR", Path.home() / "progress-log"))
MD_FILENAME = "progress-log.md"
JSONL_FILENAME = "progress-log.jsonl"

EXIT_COMMANDS = {"exit", "quit"}


def parse_entry(raw: str) -> tuple[str, list[str]]:
    text, sep, tag_part = raw.partition("--")
    text = text.strip()
    tags = [t.strip() for t in tag_part.split(",") if t.strip()] if sep else []
    return text, tags


def append_entry(md_path: Path, jsonl_path: Path, text: str, tags: list[str], when: datetime) -> None:
    timestamp_md = when.strftime("%Y-%m-%d %H:%M:%S")
    tag_suffix = f" ({', '.join(tags)})" if tags else ""
    with md_path.open("a", encoding="utf-8") as f:
        f.write(f"- [{timestamp_md}] {text}{tag_suffix}\n")
        f.flush()
        os.fsync(f.fileno())

    record = {"timestamp": when.isoformat(timespec="seconds"), "entry": text, "tags": tags}
    with jsonl_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
        f.flush()
        os.fsync(f.fileno())


def main() -> None:
    log_dir = DEFAULT_DIR
    if len(sys.argv) > 1 and sys.argv[1] == "--dir":
        if len(sys.argv) < 3:
            print("Usage: plog [--dir DIRECTORY]", file=sys.stderr)
            sys.exit(1)
        log_dir = Path(sys.argv[2])

    log_dir.mkdir(parents=True, exist_ok=True)
    md_path = log_dir / MD_FILENAME
    jsonl_path = log_dir / JSONL_FILENAME

    def show_banner() -> None:
        os.system("clear")
        print(f"Logging to {md_path} and {jsonl_path}")
        print("Type an entry below. Add tags with: message -- tag1, tag2")

    show_banner()

    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nexited")
            break

        if not raw:
            continue
        if raw.lower() in EXIT_COMMANDS:
            print("exited")
            break

        text, tags = parse_entry(raw)
        if not text:
            continue

        append_entry(md_path, jsonl_path, text, tags, datetime.now())
        show_banner()
        print("logged.")


if __name__ == "__main__":
    main()
