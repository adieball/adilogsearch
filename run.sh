#!/usr/bin/env bash
# Linux / macOS launcher
# Optional: pass the log directory as an argument to override the default.
cd "$(dirname "$0")"
exec ./venv/bin/python app.py "$@"
