# REAL EARTH SAINT-MAURICE 3 KM ULTRA — SDK source creator, non-destructive.
# Usage: .\LANCER_ULTRA_WINDOWS.ps1 [-SansOrthophoto] [-SansPaysage] [-Compiler -SDKTool ...]
param(
    [switch]$SansOrthophoto,
    [switch]$SansPaysage,
    [switch]$SansOSM,
    [switch]$SansLidar,
    [switch]$OSMObligatoire,
    [switch]$Compiler,
    [string]$SDKTool = ''
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

function Run-Python([string[]]$ArgsList) {
    & $Python @ArgsList
    if ($LASTEXITCODE -ne 0) { throw "Erreur Python : $($ArgsList -join ' ')" }
}
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Python est absent : installer Python 3.11 ou 3.12 (64 bits).'
}
if (-not (Test-Path '.venv')) { & py -3 -m venv .venv }
$Python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
Run-Python -ArgsList @('-m','pip','install','-r','requirements-ortho.txt')
Run-Python -ArgsList @('-m','pytest','-q')
Run-Python -ArgsList @('prepare_zone.py')

# Download genuine IGN BD TOPO, never rebuild from synthetic fixture.
if (-not (Test-Path 'data\ign_buildings.geojson')) {
    Run-Python -ArgsList @('generate.py','fetch')
} else {
    Write-Host 'IGN batiments locaux : utilisation des donnees existantes.'
}
$Source = 'data\ign_buildings.geojson'

# Maximum quality: automatically find real IGN 0.5m MNT/MNS tiles via public WFS.
# Downloads and mosaics are resumable. Existing user-supplied URLs remain valid.
if (-not $SansLidar -and -not ((Test-Path 'data\lidar\mnt_0m50.tif') -and (Test-Path 'data\lidar\mns_0m50.tif'))) {
    try {
        if (-not (Test-Path 'data\lidar\mnt_urls.txt') -or -not (Test-Path 'data\lidar\mns_urls.txt')) {
            Run-Python -ArgsList @('lidar_autofetch.py','discover')
        }
    } catch {
        Write-Warning "Index IGN LiDAR HD indisponible, toitures IGN conservees : $($_.Exception.Message)"
    }
}
# Optional IGN LiDAR HD 0.5 m MNT and MNS: automatically discovered or provided by user.
if (-not $SansLidar -and (Test-Path 'data\lidar\mnt_urls.txt') -and (Test-Path 'data\lidar\mns_urls.txt') -and
    ((Get-Item 'data\lidar\mnt_urls.txt').Length -gt 0) -and ((Get-Item 'data\lidar\mns_urls.txt').Length -gt 0)) {
    try {
        Run-Python -ArgsList @('lidar_download.py','data\lidar\mnt_urls.txt','--output','data\lidar\mnt')
        Run-Python -ArgsList @('lidar_download.py','data\lidar\mns_urls.txt','--output','data\lidar\mns')
        Run-Python -ArgsList @('lidar_mosaic.py','data\lidar\mnt','--output','data\lidar\mnt_0m50.tif')
        Run-Python -ArgsList @('lidar_mosaic.py','data\lidar\mns','--output','data\lidar\mns_0m50.tif')
    } catch {
        Write-Warning "Lidar telechargement/mosaique incomplet : $($_.Exception.Message). Reprendre en relancant le script."
    }
}
if (-not $SansLidar -and (Test-Path 'data\lidar\mnt_0m50.tif') -and (Test-Path 'data\lidar\mns_0m50.tif')) {
    Run-Python -ArgsList @('lidar_roofs.py','--source',$Source,
        '--mnt','data\lidar\mnt_0m50.tif','--mns','data\lidar\mns_0m50.tif',
        '--output','data\ign_buildings_lidar.geojson')
    $Source = 'data\ign_buildings_lidar.geojson'
    Write-Host 'LiDAR HD : hauteur des maisons enrichie lorsque mesure fiable.'
} else {
    Write-Host 'LiDAR HD optionnel absent : volumes de maisons fondes sur IGN BD TOPO.'
}

# Import all valid buildings from the 3000m circle (no 200-building cap).
Run-Python -ArgsList @('generate.py','build','--source',$Source,'--limit','0')
if (-not $SansPaysage) {
    Run-Python -ArgsList @('landscape.py','all')
}
# OSM details: only real mapped hedges/walls; if Overpass is rate-limited,
# keep the successful IGN build and write the error to an explicit local log.
if (-not $SansOSM) {
    try {
        if (Test-Path 'data\osm_microdetails.json') {
            Run-Python -ArgsList @('osm_microdetails.py','build')
        } else {
            Run-Python -ArgsList @('osm_microdetails.py','all')
        }
    } catch {
        $msg = "OSM non disponible : $($_.Exception.Message)"
        Write-Warning $msg
        $msg | Out-File -Encoding utf8 'osm_erreur.txt'
        if ($OSMObligatoire) { throw }
    }
}
if (-not $SansOrthophoto) {
    Write-Host 'ORTHOPHOTO IGN 20 cm : cercle complet de 3000m en 16-bit PNG LOD20.'
    Write-Host 'Le nombre de tuiles est important. Le telechargement est reprenable.'
    Run-Python -ArgsList @('fetch_ortho_ign.py','--radius','3000','--max-tiles','60000')
}
Run-Python -ArgsList @('valider_sortie.py')
Run-Python -ArgsList @('build_quality_report.py')
Write-Host 'Sources SDK construites. Aucun ancien mod ni fichier du simulateur modifie.'

$Project = Join-Path $PSScriptRoot 'output\realearth-saint-maurice-hd.xml'
if ($Compiler) {
    if (-not $SDKTool -and $env:MSFS_SDK_ROOT) {
        $candidate = Join-Path $env:MSFS_SDK_ROOT 'Tools\bin\fspackagetool.exe'
        if (Test-Path $candidate) { $SDKTool = $candidate }
    }
    if (-not $SDKTool -or -not (Test-Path $SDKTool)) {
        throw 'Compilation : fournir -SDKTool chemin\vers\fspackagetool.exe (SDK FS2024).'
    }
    & $SDKTool $Project '-nopause'
    if ($LASTEXITCODE -ne 0) { throw 'SDK compilation failed; do not install package.' }
    Write-Host 'Compilation SDK demandee : verifier ensuite les logs, textures et rendu en vol.'
} else {
    Write-Host 'Ouvrir output\realearth-saint-maurice-hd.xml dans le Project Editor FS2024.'
}
