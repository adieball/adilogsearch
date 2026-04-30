# AdiIRC Log Search

A lightweight local web app for searching [AdiIRC](https://www.adiirc.com/) log files.

- Full-text and regex search across all log files at once
- Filter by server and channel (multi-select sidebar)
- Filter by date range using timestamps inside the log files
- Results show matched lines with configurable context (3 / 5 / 10 / 20 lines)
- Open any result directly in your text editor, with line-jump support for VS Code, Kate, Sublime, Notepad++, and more

![screenshot placeholder](screenshot.png)

---

## Requirements

- Python 3.9+
- AdiIRC configured to write log files (one file per channel/server)

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/adieball/adilogsearch.git
cd adilogsearch
```

### 2. Create a virtual environment and install dependencies

**Linux / macOS**
```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

**Windows**
```cmd
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

### 3. Point the app at your log directory

AdiIRC can be configured to write logs anywhere. Tell the app where yours are using **one** of these methods (in order of priority):

#### Option A — Command-line argument
```bash
# Linux / macOS
./run.sh "/path/to/your/AdiIRC Logs"

# Windows
run.bat "C:\Users\YourName\Documents\AdiIRC\Logs"
```

#### Option B — Environment variable
```bash
# Linux / macOS
export ADIIRC_LOG_PATH="/path/to/your/AdiIRC Logs"
./run.sh

# Windows (Command Prompt)
set ADIIRC_LOG_PATH=C:\Users\YourName\Documents\AdiIRC\Logs
run.bat

# Windows (PowerShell)
$env:ADIIRC_LOG_PATH = "C:\Users\YourName\Documents\AdiIRC\Logs"
.\run.bat
```

#### Option C — Edit the default path in `app.py`

Open `app.py` and change the `DEFAULT_LOG_ROOT` line near the top:

```python
DEFAULT_LOG_ROOT = Path("/path/to/your/AdiIRC Logs")
```

### 4. Run

```bash
# Linux / macOS
chmod +x run.sh
./run.sh

# Windows
run.bat
```

The app starts a local web server and opens `http://127.0.0.1:5000` in your browser automatically.

---

## Log file format

The app expects AdiIRC's default log format:

```
[YYYY-MM-DD HH:MM:SS] <nick> message
[YYYY-MM-DD HH:MM:SS] * action or system message
```

Log files should be named `ServerName - #channel.log` or `ServerName - nickname.log`, which is the AdiIRC default. Files found in subdirectories named `Old` (case-insensitive) are marked as archived in the sidebar.

---

## Opening results in your editor

The **Open file** button opens the log file using the OS default application for `.log` files.

The **Open at line N** button tries to open the file at the exact matched line. It checks for these editors in order and uses the first one found:

| Editor | Platforms |
|--------|-----------|
| VS Code (`code`) | Windows, macOS, Linux |
| Sublime Text (`subl`) | Windows, macOS, Linux |
| Kate | Linux (KDE) |
| KWrite | Linux (KDE) |
| gedit | Linux (GNOME) |
| Geany | Linux |
| Pluma | Linux (MATE) |
| Notepad++ | Windows |
| BBEdit | macOS |

If none of these are found, it falls back to the OS default and opens at the start of the file.

---

## License

MIT
