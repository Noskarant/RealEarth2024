# Saint-Maurice-sur-Dargoire : bâtiments IGN pour le bourg et 3 km autour.
# Ne supprime ni n'édite les packages existants église, Madone, bancs, Valmorel.
param(
    [switch]$Compiler,
    [string]$SDKTool = ""
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Python 3.11/3.12 doit être installé et accessible via py.'
}
if (-not (Test-Path '.venv')) { py -3 -m venv .venv }
$Python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $Python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Installation des dépendances échouée.' }
& $Python prepare_zone.py
if ($LASTEXITCODE -ne 0) { throw 'Erreur cartographie de protection.' }
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests en erreur : génération annulée.' }
& $Python generate.py all --limit 0
if ($LASTEXITCODE -ne 0) { throw 'IGN ou génération en erreur : compilation annulée.' }
& $Python valider_sortie.py
if ($LASTEXITCODE -ne 0) { throw 'Vérification de sécurité échouée : compilation annulée.' }
Write-Host 'Sources du mod complètes (rayon 3 km). Les monuments restent protégés.'
$Project = Join-Path $PSScriptRoot 'output\realearth-saint-maurice-hd.xml'
if ($Compiler) {
    if (-not $SDKTool) {
        throw 'Compiler: préciser -SDKTool "C:\...\fspackagetool.exe" (chemin SDK installé)'
    }
    if (-not (Test-Path $SDKTool)) { throw "Compilateur SDK introuvable : $SDKTool" }
    & $SDKTool $Project '-nopause'
    if ($LASTEXITCODE -ne 0) { throw 'La compilation SDK a échoué.' }
    Write-Host 'Compilation demandée. Vérifier les logs SDK et le package avant tout déploiement.'
} else {
    Write-Host "Pour compiler avec le SDK FS2024 : .\LANCER_QUALITE_WINDOWS.ps1 -Compiler -SDKTool 'C:\...\fspackagetool.exe'"
    Write-Host 'Rien n’a été installé dans Community automatiquement.'
}
