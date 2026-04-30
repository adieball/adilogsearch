#!/usr/bin/env python3
"""AdiIRC Log Search — web app for searching AdiIRC log files.

Configure the log directory via (in order of priority):
  1. Command-line argument:  python app.py /path/to/logs
  2. Environment variable:   ADIIRC_LOG_PATH=/path/to/logs python app.py
  3. Edit LOG_ROOT below.
"""

import os
import re
import shutil
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from flask import Flask, render_template, request, jsonify

# ---------------------------------------------------------------------------
# Configuration — change this if you are not using CLI args or env vars
# ---------------------------------------------------------------------------
DEFAULT_LOG_ROOT = Path.home() / "AdiIRC Logs"

def resolve_log_root() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    env = os.environ.get("ADIIRC_LOG_PATH")
    if env:
        return Path(env)
    return DEFAULT_LOG_ROOT

LOG_ROOT = resolve_log_root()

# ---------------------------------------------------------------------------
# Editors with line-jump support, tried in order.
# {line} → line number, {file} → absolute file path.
# Cross-platform editors are listed first.
# ---------------------------------------------------------------------------
LINE_JUMP_EDITORS = [
    ("code",      ["code", "--goto", "{file}:{line}"]),       # VS Code  (Win/Mac/Linux)
    ("subl",      ["subl", "{file}:{line}"]),                  # Sublime  (Win/Mac/Linux)
    ("kate",      ["kate", "--line", "{line}", "{file}"]),     # KDE Linux
    ("kwrite",    ["kwrite", "--line", "{line}", "{file}"]),   # KDE Linux
    ("gedit",     ["gedit", "+{line}", "{file}"]),             # GNOME
    ("geany",     ["geany", "--line", "{line}", "{file}"]),    # cross-platform
    ("pluma",     ["pluma", "+{line}", "{file}"]),             # MATE
    ("notepad++", ["notepad++", "-n{line}", "{file}"]),        # Windows
    ("bbedit",    ["bbedit", "+{line}", "{file}"]),            # macOS
]

LINE_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2})")

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Log scanning
# ---------------------------------------------------------------------------

def scan_logs():
    """Scan LOG_ROOT recursively and return a server→channels structure."""
    servers: dict = {}

    for log_file in sorted(LOG_ROOT.rglob("*.log")):
        name = log_file.stem          # e.g. "FuelRats - #fuelrats"
        parts = name.split(" - ", 1)
        if len(parts) == 2:
            server, channel = parts
        else:
            server, channel = log_file.parent.name, name

        rel = log_file.relative_to(LOG_ROOT)
        archived = any(p.lower() == "old" for p in rel.parts[:-1])
        label = channel + (" [old]" if archived else "")

        servers.setdefault(server, []).append({
            "label": label,
            "channel": channel,
            "path": str(log_file),
            "archived": archived,
        })

    for s in servers:
        servers[s].sort(key=lambda x: (x["archived"], x["label"].lower()))

    return dict(sorted(servers.items()))


# ---------------------------------------------------------------------------
# Searching
# ---------------------------------------------------------------------------

def parse_line_dates(lines):
    """Return a date string (YYYY-MM-DD) for each line, inheriting the last
    seen timestamp for lines that have none."""
    dates = []
    last = None
    for line in lines:
        m = LINE_RE.match(line)
        if m:
            last = m.group(1)
        dates.append(last)
    return dates


def search_file(filepath, pattern, context, use_regex, case_sensitive,
                date_from=None, date_to=None):
    """Search one file; return a list of match-block dicts."""
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return []

    flags = 0 if case_sensitive else re.IGNORECASE
    if use_regex:
        try:
            rx = re.compile(pattern, flags)
        except re.error:
            return []
        match_fn = lambda line: bool(rx.search(line))
    else:
        needle = pattern if case_sensitive else pattern.lower()
        match_fn = lambda line: needle in (line if case_sensitive else line.lower())

    date_filter = bool(date_from or date_to)
    if date_filter:
        line_dates = parse_line_dates(lines)

    matched_lines = set()
    for i, line in enumerate(lines):
        if date_filter:
            d = line_dates[i]
            if d is None:
                continue
            if date_from and d < date_from:
                continue
            if date_to and d > date_to:
                continue
        if match_fn(line):
            matched_lines.add(i)

    if not matched_lines:
        return []

    # Group nearby matches to avoid duplicated context
    sorted_matches = sorted(matched_lines)
    raw_blocks = [[sorted_matches[0]]]
    for m in sorted_matches[1:]:
        if m - raw_blocks[-1][-1] <= context * 2:
            raw_blocks[-1].append(m)
        else:
            raw_blocks.append([m])

    results = []
    for block in raw_blocks:
        first_match = block[0]
        last_match = block[-1]
        start = max(0, first_match - context)
        end = min(len(lines), last_match + context + 1)
        excerpt = [
            {
                "lineno": i + 1,
                "text": lines[i].rstrip("\n"),
                "is_match": i in matched_lines,
            }
            for i in range(start, end)
        ]
        results.append({
            "start_line": start + 1,
            "first_match_line": first_match + 1,
            "lines": excerpt,
        })

    return results


# ---------------------------------------------------------------------------
# OS helpers
# ---------------------------------------------------------------------------

def _launch(cmd):
    """Start a detached process (cross-platform)."""
    if sys.platform == "win32":
        subprocess.Popen(
            cmd,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    else:
        subprocess.Popen(cmd, start_new_session=True)


def _open_default(path):
    """Open a file with the OS default associated application."""
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        _launch(["open", path])
    else:
        _launch(["xdg-open", path])


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    tree = scan_logs()
    return render_template("index.html", tree=tree, log_root=str(LOG_ROOT))


@app.route("/search", methods=["POST"])
def search():
    data = request.get_json()
    query = data.get("query", "").strip()
    paths = data.get("paths", [])
    context = int(data.get("context", 5))
    use_regex = bool(data.get("use_regex", False))
    case_sensitive = bool(data.get("case_sensitive", False))
    date_from = data.get("date_from", "").strip() or None
    date_to = data.get("date_to", "").strip() or None

    if not query or not paths:
        return jsonify([])

    results = []
    for path in paths:
        try:
            Path(path).relative_to(LOG_ROOT)
        except ValueError:
            continue
        blocks = search_file(path, query, context, use_regex, case_sensitive,
                             date_from, date_to)
        if blocks:
            results.append({"filename": path, "blocks": blocks})

    return jsonify(results)


@app.route("/open", methods=["POST"])
def open_file():
    data = request.get_json()
    path = data.get("path", "")
    line = int(data.get("line", 1))
    jump = bool(data.get("jump", False))

    try:
        Path(path).relative_to(LOG_ROOT)
    except ValueError:
        return jsonify({"error": "Invalid path"}), 400

    if jump:
        for binary, cmd_template in LINE_JUMP_EDITORS:
            if shutil.which(binary):
                cmd = [
                    part.replace("{line}", str(line)).replace("{file}", path)
                    for part in cmd_template
                ]
                _launch(cmd)
                return jsonify({"ok": True, "editor": binary, "line_supported": True})
        # No line-aware editor found — fall through to default
        _open_default(path)
        return jsonify({"ok": True, "editor": "default", "line_supported": False})

    _open_default(path)
    return jsonify({"ok": True, "editor": "default", "line_supported": False})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _open_browser():
    import time
    time.sleep(0.8)
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    if not LOG_ROOT.exists():
        print(f"Error: log directory not found: {LOG_ROOT}")
        print("Usage: python app.py /path/to/your/AdiIRC/logs")
        print("  or:  set ADIIRC_LOG_PATH=/path/to/logs and run python app.py")
        sys.exit(1)

    print(f"Log directory: {LOG_ROOT}")
    threading.Thread(target=_open_browser, daemon=True).start()
    print("AdiIRC Log Search running at http://127.0.0.1:5000")
    app.run(debug=False, port=5000)
