# Executer sous PowerShell depuis le dossier de ce prototype.
# Le premier lancement telecharge les emprises de l'IGN (connexion necessaire).
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.venv')) { py -3 -m venv .venv }
& '.\.venv\Scripts\python.exe' -m pip install --upgrade pip
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
& '.\.venv\Scripts\python.exe' generate.py all
if ($LASTEXITCODE -ne 0) { throw 'Generation interrompue : consulter les erreurs ci-dessus.' }
Write-Host 'Projet genere dans output\. Ouvrir output\realearth-saint-maurice-hd.xml dans le SDK de MSFS2024.'
