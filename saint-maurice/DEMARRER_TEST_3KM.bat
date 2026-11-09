@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0LANCER_QUALITE_WINDOWS.ps1"
if errorlevel 1 (
  echo.
  echo ECHEC: lire les messages ci-dessus avant de reessayer.
) else (
  echo.
  echo Preparation reussie. Ouvrir output\realearth-saint-maurice-hd.xml dans le SDK FS2024.
)
pause
