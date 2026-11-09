@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0LANCER_ULTRA_WINDOWS.ps1"
if errorlevel 1 (
  echo.
  echo ECHEC: consulter le message ci-dessus. Aucun ancien mod ne doit etre modifie.
) else (
  echo.
  echo Terminé : sources generees. Compiler avec le SDK FS2024 et verifier en vol.
)
pause
