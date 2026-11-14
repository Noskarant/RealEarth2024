# MSFS2024 Valmorel telecabines. Source assets distributed separately as ZIP.
# Build+install only own addon; never modify other scenery or old realearth-valmorel-hd.
[CmdletBinding()]
param([string]$CommunityPath='C:\Users\anter\AppData\Local\Packages\Microsoft.Limitless_8wekyb3d8bbwe\LocalCache\Packages\Community',
      [switch]$BuildOnly)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$Root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$Name='realearth-valmorel-telecabines'
$Project=Join-Path $Root 'project\valmorel-telecabines.xml'
$Built=Join-Path $Root ('project\Packages\'+$Name)
$Target=Join-Path $CommunityPath $Name
$Stage=$null
$Held=$null
$PreviousMoved=$false
$Completed=$false
function Call-Py([string]$relative) {
  if (Test-Path -LiteralPath 'D:\RealEarth2024\.venv\Scripts\python.exe') {
    & 'D:\RealEarth2024\.venv\Scripts\python.exe' (Join-Path $Root $relative)
  } elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 (Join-Path $Root $relative)
  } else {
    throw 'Python 3 introuvable.'
  }
  if ($LASTEXITCODE -ne 0) { throw "Erreur Python : $relative" }
}
try {
  if (@(Get-Process -Name @('FlightSimulator2024','FlightSimulator') -ErrorAction SilentlyContinue).Count -gt 0) { throw 'Fermer FS2024 avant compilation.' }
  if (-not (Test-Path -LiteralPath $CommunityPath -PathType Container)) { throw "Community absent: $CommunityPath" }
  if (-not (Test-Path -LiteralPath $Project -PathType Leaf)) { throw "Projet SDK manquant: $Project" }
  $Sdk='D:\RealEarth2024\build\tools\fspackagetool.exe'
  if (-not (Test-Path -LiteralPath $Sdk -PathType Leaf)) {
    $sdkRoot=[Environment]::GetEnvironmentVariable('MSFS2024_SDK')
    if ($sdkRoot) {$Sdk=Join-Path $sdkRoot 'Tools\bin\fspackagetool.exe'}
  }
  if (-not (Test-Path -LiteralPath $Sdk -PathType Leaf)) {throw 'SDK fspackagetool.exe introuvable (non redistribuable).'}
  Call-Py 'scripts\prepare_sdk.py'
  Call-Py 'scripts\prepare_placements.py'
  if (Test-Path -LiteralPath $Built) { Remove-Item -LiteralPath $Built -Recurse -Force }
  & $Sdk $Project '-rebuild' '-nopause'
  if ($LASTEXITCODE -ne 0) { throw "Erreur de compilation SDK ($LASTEXITCODE)" }
  $deadline=(Get-Date).AddMinutes(6)
  $stable=0
  $last=''
  do {
    if ((Test-Path (Join-Path $Built 'manifest.json')) -and (Test-Path (Join-Path $Built 'layout.json'))) {
      $files=@(Get-ChildItem -LiteralPath $Built -File -Recurse)
      $now=($files | Sort-Object FullName | ForEach-Object { "$($_.FullName):$($_.Length):$($_.LastWriteTimeUtc.Ticks)" }) -join '|'
      if ($now -eq $last -and $files.Count -ge 4) {$stable++} else {$stable=0;$last=$now}
      if ($stable -ge 2) {break}
    }
    Start-Sleep -Seconds 2
  } while ((Get-Date) -lt $deadline)
  if ($stable -lt 2) {throw 'Fichiers SDK incomplets ou non stabilises.'}
  $layout=Get-Content -LiteralPath (Join-Path $Built 'layout.json') -Raw | ConvertFrom-Json
  $manifest=Get-Content -LiteralPath (Join-Path $Built 'manifest.json') -Raw | ConvertFrom-Json
  if ("$($manifest.package_version)" -ne '0.1.0') { throw 'Mauvaise version.' }
  if (@(Get-ChildItem -LiteralPath $Built -Filter '*.glb' -File -Recurse).Count -lt 8) {throw 'Moins de 8 modeles compiles.'}
  if (@(Get-ChildItem -LiteralPath $Built -Filter '*.bgl' -File -Recurse).Count -lt 1) {throw 'BGL manquant.'}
  $entries=@($layout.content)
  if ($entries.Count -lt 2) { throw 'Layout vide.' }
  foreach ($entry in $entries) {
    $rel=[string]$entry.path
    if ([IO.Path]::IsPathRooted($rel) -or $rel.Contains('..')) { throw "Chemin layout invalide : $rel" }
    $file=Join-Path $Built ($rel -replace '/', '\')
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {throw "Absent : $rel"}
    if ((Get-Item -LiteralPath $file).Length -ne [long]$entry.size) {throw "Taille incorrecte : $rel"}
  }
  if ($BuildOnly) {Write-Host 'Compilation seule terminee.'; exit 0}
  if (@(Get-Process -Name @('FlightSimulator2024','FlightSimulator') -ErrorAction SilentlyContinue).Count -gt 0) {throw 'FS2024 lance pendant le build.'}
  $id=[guid]::NewGuid().ToString('N').Substring(0,8)
  $Stage=Join-Path $CommunityPath ('.'+$Name+'_stage_'+$id)
  $Held=Join-Path $CommunityPath ('.'+$Name+'_old_'+$id)
  Copy-Item -LiteralPath $Built -Destination $Stage -Recurse
  if (-not (Test-Path (Join-Path $Stage 'manifest.json'))) {throw 'Copie incomplet.'}
  if (Test-Path -LiteralPath $Target) {
    $backup=Join-Path $Root ('backups\'+$Name+'_'+(Get-Date -Format 'yyyyMMdd_HHmmss')+'_'+$id)
    New-Item -ItemType Directory -Path (Split-Path $backup) -Force | Out-Null
    Copy-Item -LiteralPath $Target -Destination $backup -Recurse
    Move-Item -LiteralPath $Target -Destination $Held
    $PreviousMoved=$true
  }
  Move-Item -LiteralPath $Stage -Destination $Target
  $Completed=$true
  if (Test-Path -LiteralPath $Held) {Remove-Item -LiteralPath $Held -Recurse -Force}
  Write-Host "Installe : $Target" -ForegroundColor Green
  Write-Host 'Gares en positions provisoires; aucun relief ni batiment modifie.' -ForegroundColor Yellow
  exit 0
} catch {
  Write-Host ("ECHEC : "+$_.Exception.Message) -ForegroundColor Red
  if ($PreviousMoved -and -not $Completed -and $Held -and (Test-Path -LiteralPath $Held)) {
    if (Test-Path -LiteralPath $Target) {Remove-Item -LiteralPath $Target -Recurse -Force}
    Move-Item -LiteralPath $Held -Destination $Target
  }
  if ($Stage -and (Test-Path -LiteralPath $Stage)) {Remove-Item -LiteralPath $Stage -Recurse -Force}
  exit 1
}
