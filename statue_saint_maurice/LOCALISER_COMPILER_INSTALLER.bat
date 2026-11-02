@echo off
setlocal
cd /d "%~dp0"
set "PYEXE=D:\RealEarth2024\.venv\Scripts\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"
echo.
echo =========================================================
echo   VIERGE SAINT-MAURICE - GPS, SDK, INSTALLATION FS2024
echo =========================================================
echo Ferme MSFS 2024 avant de lancer ce programme.
echo.
"%PYEXE%" "%~dp0resolve_google_maps.py"
if errorlevel 1 goto :error
"%PYEXE%" "%~dp0compile_statue.py"
if errorlevel 1 goto :error
"%PYEXE%" "%~dp0install_statue.py"
if errorlevel 1 goto :error
echo.
echo SUCCES - tu peux ouvrir FS2024 pour verifier la statue.
goto :end
:error
echo.
echo ECHEC - Community et les autres addons restent inchanges.
:end
echo.
pause
