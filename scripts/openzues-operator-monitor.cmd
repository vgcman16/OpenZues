@echo off
setlocal EnableDelayedExpansion

chcp 65001 >nul

set "ROOT=%~dp0.."
set "SCRIPT=%ROOT%\scripts\openzues-operator-monitor.ps1"
set "ARGS="

if not exist "%SCRIPT%" (
    echo Missing operator monitor script at "%SCRIPT%".
    exit /b 1
)

:parse
if "%~1"=="" goto run
if /I "%~1"=="--port" (
    set "ARGS=!ARGS! -Port %~2"
    shift
    shift
    goto parse
)
if /I "%~1"=="--cycles" (
    set "ARGS=!ARGS! -Cycles %~2"
    shift
    shift
    goto parse
)
if /I "%~1"=="--interval" (
    set "ARGS=!ARGS! -IntervalSeconds %~2"
    shift
    shift
    goto parse
)
if /I "%~1"=="--browser-every" (
    set "ARGS=!ARGS! -BrowserEvery %~2"
    shift
    shift
    goto parse
)
set "ARGS=!ARGS! %~1"
shift
goto parse

:run
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" !ARGS!
