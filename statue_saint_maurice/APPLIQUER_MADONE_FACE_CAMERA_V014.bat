@echo off
setlocal
cd /d "%~dp0"
echo ====================================================
echo   MADONE SAINT-MAURICE - +90 degres, 2 m vers toi
echo ====================================================
echo Verifie que MSFS 2024 est ferme.
set "PYEXE=D:\RealEarth2024\.venv\Scripts\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"
"%PYEXE%" "%~dp0corriger_madone_face_camera_v014.py"
if errorlevel 1 (
  echo.
  echo ECHEC : consulte le message ci-dessus. Pas de modification de Valmorel.
) else (
  echo.
  echo OK : ouvre MSFS 2024 et compare depuis le meme point.
)
pause
