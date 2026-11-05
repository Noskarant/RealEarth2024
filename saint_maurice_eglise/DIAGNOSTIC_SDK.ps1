$ErrorActionPreference = 'Continue'
Write-Host "=== Diagnostic MSFS2024 / SDK (lecture seule) ===" -ForegroundColor Cyan
$p = Get-AppxPackage -Name 'Microsoft.Limitless' -ErrorAction SilentlyContinue
if ($null -eq $p) {
  Write-Host 'MSFS 2024 Store non trouve pour cet utilisateur (version Steam possible).' -ForegroundColor Yellow
} else {
  Write-Host ('Version enregistree : ' + $p.Version)
  Write-Host ('Chemin Windows      : ' + $p.InstallLocation)
  Write-Host ('Package complet     : ' + $p.PackageFullName)
  Write-Host ('Dossier detectable  : ' + (Test-Path -LiteralPath $p.InstallLocation))
  Write-Host 'NB : WindowsApps est protege ; un Test-Path negatif ne prouve pas une desinstallation.'
}
$g = Get-AppxPackage -Name 'Microsoft.GamingServices' -ErrorAction SilentlyContinue
if ($null -ne $g) { Write-Host ('Gaming Services     : ' + $g.Version) }
else { Write-Host 'Gaming Services non detecte pour cet utilisateur.' -ForegroundColor Yellow }
Write-Host 'SDK attendu sur ce PC: D:\RealEarth2024\build\tools\fspackagetool.exe'
Write-Host ('SDK present : ' + (Test-Path -LiteralPath 'D:\RealEarth2024\build\tools\fspackagetool.exe'))
Write-Host ''
Write-Host 'Si le SDK reclame un dossier WindowsApps Microsoft.Limitless_1.9.21.0...' -ForegroundColor Yellow
Write-Host 'Comparez la version / InstallLocation ci-dessus au message derreur de compilation.'
Write-Host 'Ne modifiez pas les permissions de WindowsApps ni les dossiers Community.'
