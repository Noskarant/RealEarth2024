@echo off
setlocal
cd /d "%~dp0"
echo.
echo =============================================================
echo   VALMOREL HD - MAJ COMPLETE POUR MSFS 2024
echo =============================================================
echo.
echo Fermer completement MSFS 2024 avant de continuer.
echo Le programme va actualiser, compiler, verifier et installer.
echo La version precedente est sauvegardee automatiquement.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\maj_valmorel.ps1"
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" (
  echo ECHEC : aucun remplacement definitif sans validation.
  echo Consulter le message d'erreur ci-dessus.
) else (
  echo TERMINE : la scene Valmorel est installee. Vous pouvez ouvrir FS2024.
)
echo.
pause
exit /b %RESULT%
