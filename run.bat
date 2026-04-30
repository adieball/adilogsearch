@echo off
:: Windows launcher
:: Optional: pass the log directory as an argument to override the default.
cd /d "%~dp0"
venv\Scripts\python app.py %*
