@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Missing .venv. Follow LOCAL_SETUP.md first.
    exit /b 1
)
".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000 --settings=tg1.settings_local
