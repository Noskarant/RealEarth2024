@echo off
setlocal
cd /d "%~dp0"
echo ==============================================
echo  SAINT MAURICE - EGLISE UNIQUEMENT - MSFS2024
echo ==============================================
echo Fermer Microsoft Flight Simulator 2024.
echo Ce programme ne modifie PAS la Madone, les bancs ou la vegetation.
echo.
where py >nul 2>&1
if not errorlevel 1 (
  py -3 "%~dp0build_install.py" --install
) else (
  where python >nul 2>&1
  if not errorlevel 1 (
    python "%~dp0build_install.py" --install
  ) else (
    echo Python 3 est requis. Installer Python puis relancer.
    pause
    exit /b 1
  )
)
if errorlevel 1 (
  echo ECHEC OU VERIFICATION REQUISE. Aucun autre add-on ne doit etre modifie.
) else (
  echo TERMINE. Ouvrir FS2024 et verifier l'eglise.
)
pause
