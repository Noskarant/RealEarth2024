@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0DIAGNOSTIC_SDK.ps1"
echo.
pause
