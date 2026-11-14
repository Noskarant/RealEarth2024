@echo off
setlocal
cd /d "%~dp0"
echo VALMOREL : installer la compilation deja reussie.
echo Ne pas lancer FS2024. Ce script ne modifie aucun batiment.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\compiler_installer.ps1" -InstallExisting
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo ECHEC : installation non terminee.
if "%RESULT%"=="0" echo Installation effectuee, controle visuel FS2024 necessaire.
pause
exit /b %RESULT%
