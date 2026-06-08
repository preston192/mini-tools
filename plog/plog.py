#!/usr/bin/env python3
"""Interactive progress logger: appends timestamped entries to a markdown and a JSONL file."""

import curses
import json
import os
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_DIR = Path(os.environ.get("PLOG_DIR", Path.home() / "progress-log"))
MD_FILENAME = "progress-log.md"
JSONL_FILENAME = "progress-log.jsonl"
TODO_SESSIONS_DIRNAME = "todo_sessions"

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


def load_todos(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        todos = json.load(f)
    for item in todos:
        item.setdefault("created_at", None)
        item.setdefault("completed_at", None)
        item.setdefault("level", 0)
    return todos


MAX_INDENT_LEVEL = 4


def save_todos(path: Path, todos: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(todos, f, indent=2)
        f.flush()
        os.fsync(f.fileno())


def safe_session_name(name: str) -> str:
    return "".join(c for c in name.strip() if c.isalnum() or c in (" ", "-", "_")).strip()


def init_colors() -> dict[str, int]:
    """Sets up color pairs and returns named attributes for consistent styling."""
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)     # title bars
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)    # selected row
    curses.init_pair(3, curses.COLOR_CYAN, -1)                     # accents / checkmarks
    curses.init_pair(4, curses.COLOR_BLACK, -1)                    # done items (shaded darker)
    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE)     # footer / help bar
    return {
        "title": curses.color_pair(1) | curses.A_BOLD,
        "selected": curses.color_pair(2) | curses.A_BOLD,
        "accent": curses.color_pair(3) | curses.A_BOLD,
        "done": curses.color_pair(4) | curses.A_BOLD,
        "footer": curses.color_pair(5),
        "dim": curses.A_DIM,
    }


def fill_bar(stdscr, y: int, text: str, attr: int) -> None:
    """Paints a full-width bar so the background fills consistently across terminals."""
    height, width = stdscr.getmaxyx()
    line = text[: width - 1].ljust(width - 1)
    try:
        stdscr.addstr(y, 0, line, attr)
    except curses.error:
        pass


def list_sessions(sessions_dir: Path) -> list[str]:
    if not sessions_dir.exists():
        return []
    return sorted(p.stem for p in sessions_dir.glob("*.json"))


def choose_session(stdscr, sessions_dir: Path, colors: dict[str, int]) -> Path | None:
    """Shows the list of sessions plus a 'new session' option.

    Returns the path to the chosen (or newly created) session file,
    or None if the user cancelled (Esc) — meaning quit the program.
    """
    while True:
        names = list_sessions(sessions_dir)
        entries = names + ["+ New session"]
        selected = 0

        while True:
            stdscr.erase()
            height, width = stdscr.getmaxyx()
            fill_bar(stdscr, 0, "  plog — sessions", colors["title"])
            fill_bar(stdscr, 1, "", colors["title"])

            if not names:
                stdscr.addstr(3, 2, "No sessions yet — create one below.", colors["dim"])
            for row, entry in enumerate(entries):
                is_new = entry == "+ New session"
                label = f"  + {entry[2:]}" if is_new else f"    {entry}"
                if row == selected:
                    fill_bar(stdscr, 3 + row, label, colors["selected"])
                else:
                    attr = colors["accent"] if is_new else curses.A_NORMAL
                    stdscr.addstr(3 + row, 0, label[: width - 1], attr)

            fill_bar(stdscr, height - 1, "  ↑/↓ move   enter select   n new session   esc quit", colors["footer"])
            stdscr.refresh()

            key = stdscr.getch()
            if key in (curses.KEY_UP, ord("k")):
                selected = max(0, selected - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                selected = min(len(entries) - 1, selected + 1)
            elif key == ord("n"):
                selected = len(entries) - 1
                break
            elif key in (10, 13, curses.KEY_ENTER):
                break
            elif key == 27:
                return None

        if entries[selected] == "+ New session":
            name = edit_line(stdscr, height - 2, "New session name: ")
            name = safe_session_name(name) if name else None
            if not name:
                continue
            session_path = sessions_dir / f"{name}.json"
            if session_path.exists():
                continue
            sessions_dir.mkdir(parents=True, exist_ok=True)
            save_todos(session_path, [])
            return session_path
        else:
            return sessions_dir / f"{entries[selected]}.json"


def confirm(stdscr, y: int, prompt: str) -> bool:
    """Asks a yes/no question on the given row. Returns True only for 'y'."""
    height, width = stdscr.getmaxyx()
    stdscr.move(y, 0)
    stdscr.clrtoeol()
    stdscr.addstr(y, 0, (prompt + " (y/n) ")[: width - 1])
    stdscr.refresh()
    while True:
        ch = stdscr.getch()
        if ch in (ord("y"), ord("Y")):
            return True
        if ch in (ord("n"), ord("N"), 27):
            return False


def edit_line(stdscr, y: int, prompt: str, initial: str = "") -> str | None:
    """A small inline text editor. Returns the entered text, or None if cancelled."""
    curses.curs_set(1)
    buffer = list(initial)
    cursor = len(buffer)
    height, width = stdscr.getmaxyx()

    while True:
        stdscr.move(y, 0)
        stdscr.clrtoeol()
        line = (prompt + "".join(buffer))[: width - 1]
        stdscr.addstr(y, 0, line)
        stdscr.move(y, min(len(prompt) + cursor, width - 1))
        stdscr.refresh()

        ch = stdscr.getch()
        if ch in (10, 13, curses.KEY_ENTER):
            curses.curs_set(0)
            return "".join(buffer).strip()
        elif ch == 27:  # Esc
            curses.curs_set(0)
            return None
        elif ch in (curses.KEY_BACKSPACE, 127, 8):
            if cursor > 0:
                del buffer[cursor - 1]
                cursor -= 1
        elif ch == curses.KEY_LEFT:
            cursor = max(0, cursor - 1)
        elif ch == curses.KEY_RIGHT:
            cursor = min(len(buffer), cursor + 1)
        elif 32 <= ch <= 126:
            buffer.insert(cursor, chr(ch))
            cursor += 1


def edit_session(stdscr, session_path: Path, sessions_dir: Path, colors: dict[str, int]) -> None:
    curses.curs_set(0)
    todos = load_todos(session_path)
    selected = 0
    offset = 0
    status = ""

    help_text = "  a add   e edit   d delete   space/enter toggle   tab/shift-tab indent   s save as…   q back"

    while True:
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        list_top = 3
        list_height = max(height - list_top - 1, 1)

        title = f"  plog — {session_path.stem}"
        if status:
            title = f"{title}   ·   {status}"
            status = ""
        fill_bar(stdscr, 0, title, colors["title"])
        fill_bar(stdscr, 1, "", colors["title"])

        if selected < offset:
            offset = selected
        elif selected >= offset + list_height:
            offset = selected - list_height + 1

        if not todos:
            stdscr.addstr(list_top, 2, "No items yet — press 'a' to add one.", colors["dim"])
        else:
            for row, idx in enumerate(range(offset, min(offset + list_height, len(todos)))):
                item = todos[idx]
                checkbox = "✓" if item["done"] else "○"
                indent = "    " + "  " * item.get("level", 0)
                label = f"{indent}{checkbox}  {item['text']}"
                if idx == selected:
                    fill_bar(stdscr, list_top + row, label, colors["selected"])
                else:
                    attr = colors["done"] if item["done"] else curses.A_NORMAL
                    stdscr.addstr(list_top + row, 0, label[: width - 1], attr)

        fill_bar(stdscr, height - 1, help_text, colors["footer"])
        stdscr.refresh()

        key = stdscr.getch()

        if key in (curses.KEY_UP, ord("k")):
            if todos:
                selected = max(0, selected - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            if todos:
                selected = min(len(todos) - 1, selected + 1)
        elif key == ord("a"):
            text = edit_line(stdscr, height - 2, "New task: ")
            if text:
                now = datetime.now().isoformat(timespec="seconds")
                level = todos[selected].get("level", 0) if todos else 0
                todos.append({
                    "text": text,
                    "done": False,
                    "created_at": now,
                    "completed_at": None,
                    "level": level,
                })
                selected = len(todos) - 1
                save_todos(session_path, todos)
        elif key == ord("\t") and todos:
            item = todos[selected]
            item["level"] = min(MAX_INDENT_LEVEL, item.get("level", 0) + 1)
            save_todos(session_path, todos)
        elif key == curses.KEY_BTAB and todos:
            item = todos[selected]
            item["level"] = max(0, item.get("level", 0) - 1)
            save_todos(session_path, todos)
        elif key == ord("e") and todos:
            text = edit_line(stdscr, height - 2, "Edit task: ", initial=todos[selected]["text"])
            if text:
                todos[selected]["text"] = text
                save_todos(session_path, todos)
        elif key == ord("d") and todos:
            del todos[selected]
            selected = max(0, min(selected, len(todos) - 1))
            save_todos(session_path, todos)
        elif key in (ord(" "), 10, 13, curses.KEY_ENTER) and todos:
            item = todos[selected]
            item["done"] = not item["done"]
            item["completed_at"] = datetime.now().isoformat(timespec="seconds") if item["done"] else None
            save_todos(session_path, todos)
        elif key == ord("s"):
            name = edit_line(stdscr, height - 2, "Save as: ")
            name = safe_session_name(name) if name else None
            if name:
                target_path = sessions_dir / f"{name}.json"
                if target_path.exists() and not confirm(stdscr, height - 2, f"Session '{name}' already exists — overwrite?"):
                    status = "save cancelled"
                else:
                    sessions_dir.mkdir(parents=True, exist_ok=True)
                    save_todos(target_path, todos)
                    status = f"saved as '{name}'"
        elif key == ord("q"):
            save_todos(session_path, todos)
            break


def run_todo_mode(stdscr, sessions_dir: Path) -> None:
    colors = init_colors()
    while True:
        session_path = choose_session(stdscr, sessions_dir, colors)
        if session_path is None:
            break
        edit_session(stdscr, session_path, sessions_dir, colors)


def main() -> None:
    args = sys.argv[1:]
    todo_requested = False
    if args and args[0] == "todo":
        todo_requested = True
        args = args[1:]

    log_dir = DEFAULT_DIR
    if args and args[0] == "--dir":
        if len(args) < 2:
            print("Usage: plog [todo] [--dir DIRECTORY]", file=sys.stderr)
            sys.exit(1)
        log_dir = Path(args[1])

    log_dir.mkdir(parents=True, exist_ok=True)
    md_path = log_dir / MD_FILENAME
    jsonl_path = log_dir / JSONL_FILENAME
    sessions_dir = log_dir / TODO_SESSIONS_DIRNAME

    if todo_requested:
        curses.wrapper(run_todo_mode, sessions_dir)
        return

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
