@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo TEST DE LA VIERGE SAINT-MAURICE - SDK OFFICIEL MSFS 2024
echo ============================================================
set "PYCMD=D:\RealEarth2024\.venv\Scripts\python.exe"
if not exist "%PYCMD%" set "PYCMD=python"
"%PYCMD%" "%~dp0compile_statue.py"
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" (
  echo ERREUR : aucun remplacement Community effectue.
) else (
  echo OK : compilation et verification terminees. Community inchange.
)
pause
exit /b %EXITCODE%
