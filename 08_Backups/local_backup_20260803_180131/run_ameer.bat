@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    python -m venv .venv
)
call .venv\Scripts\activate
python -m pip install -r requirements.txt
python start_ameer.py
exit /b %ERRORLEVEL%
