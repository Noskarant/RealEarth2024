@echo off
setlocal
cd /d "%~dp0"
echo VALMOREL - TELECABINES Planchamp / Pierrafort - Apercu statique
echo Fermer MSFS 2024 avant de continuer.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\compiler_installer.ps1"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo ECHEC : ne pas ouvrir le simulateur avant d'avoir lu les erreurs.
if "%RESULT%"=="0" echo TERMINE : verifiez les gares en jeu, les positions sont provisoires.
pause
exit /b %RESULT%
