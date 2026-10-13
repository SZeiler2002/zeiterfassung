@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    echo Bitte zuerst die Einrichtung aus README.md ausfuehren.
    pause
    exit /b 1
)
.venv\Scripts\python.exe manage.py migrate
if errorlevel 1 (
    pause
    exit /b 1
)
echo Zeitkonto startet auf http://127.0.0.1:8000
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
pause
