@echo off
setlocal

set "ROOT=%~dp0.."
set "PYTHON=%ROOT%\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Missing virtualenv Python at "%PYTHON%".
    echo Create the repo virtualenv first, then rerun this watcher.
    exit /b 1
)

"%PYTHON%" -m openzues.cli watch %*
