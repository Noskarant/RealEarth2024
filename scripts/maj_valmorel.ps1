# Valmorel MSFS 2024: safe one-click rebuild, verify, backup and install.
# Run via MAJ_VALMOREL.bat. Keep FS2024 CLOSED during the installation.
# The script does not edit UserCfg.opt, unrelated add-ons, or the game files.

[CmdletBinding()]
param(
    [string]$CommunityPath = "",
    [switch]$SkipGitPull
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Sdk = Join-Path $Root "build\tools\fspackagetool.exe"
$ProjectXml = Join-Path $Root "project\realearth-valmorel-hd.xml"
$PackageDefinition = Join-Path $Root "project\PackageDefinitions\realearth-valmorel-hd.xml"
$Compiled = Join-Path $Root "project\Packages\realearth-valmorel-hd"
$Dist = Join-Path $Root "dist\realearth-valmorel-hd"
$PackageName = "realearth-valmorel-hd"
$ExpectedBranch = "fix/valmorel-sdk-textures"
$BackupRoot = Join-Path $Root "build\backups\community"
$community = $null
$stage = $null
$held = $null
$installationFinished = $false
$previousMoved = $false

function Step([string]$Message) {
    Write-Host ""
    Write-Host ("==> " + $Message) -ForegroundColor Cyan
}

function Run-Python([string]$RelativeScript) {
    $target = Join-Path $Root $RelativeScript
    if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
        throw "Python script is missing: $target"
    }
    & $Python $target
    if ($LASTEXITCODE -ne 0) {
        throw "Python step failed (exit $LASTEXITCODE): $RelativeScript"
    }
}

function Find-Community([string]$Override) {
    if (-not [string]::IsNullOrWhiteSpace($Override)) {
        $given = [Environment]::ExpandEnvironmentVariables($Override)
        if (-not (Test-Path -LiteralPath $given -PathType Container)) {
            throw "The -CommunityPath folder does not exist: $given"
        }
        return (Resolve-Path -LiteralPath $given).Path
    }

    # MSFS 2024 documents InstalledPackagesPath in UserCfg.opt.
    $cfgPaths = @(
        (Join-Path $env:LOCALAPPDATA "Packages\Microsoft.Limitless_8wekyb3d8bbwe\LocalCache\UserCfg.opt"),
        (Join-Path $env:APPDATA "Microsoft Flight Simulator 2024\UserCfg.opt")
    )
    $configuredRoots = @()
    foreach ($cfg in $cfgPaths) {
        if (-not (Test-Path -LiteralPath $cfg -PathType Leaf)) { continue }
        $content = Get-Content -LiteralPath $cfg -Raw
        $match = [regex]::Match(
            $content, '(?m)^\s*InstalledPackagesPath\s+"([^"]+)"\s*$'
        )
        if ($match.Success) {
            $configuredRoots += [Environment]::ExpandEnvironmentVariables(
                $match.Groups[1].Value
            )
        }
    }

    $paths = @()
    if ($configuredRoots.Count -gt 0) {
        foreach ($base in ($configuredRoots | Select-Object -Unique)) {
            foreach ($folder in @("Community", "Community2024")) {
                $paths += Join-Path $base $folder
            }
        }
    } else {
        $paths += Join-Path $env:LOCALAPPDATA "Packages\Microsoft.Limitless_8wekyb3d8bbwe\LocalCache\Packages\Community"
        $paths += Join-Path $env:APPDATA "Microsoft Flight Simulator 2024\Packages\Community"
    }

    $existingDirs = @(
        $paths | Where-Object { Test-Path -LiteralPath $_ -PathType Container } |
            ForEach-Object { (Resolve-Path -LiteralPath $_).Path } |
            Select-Object -Unique
    )
    $containingOldPackage = @(
        $existingDirs | Where-Object {
            Test-Path -LiteralPath (Join-Path $_ $PackageName) -PathType Container
        }
    )
    if ($containingOldPackage.Count -eq 1) {
        return $containingOldPackage[0]
    }
    if ($containingOldPackage.Count -gt 1) {
        throw "Multiple Community folders contain this add-on. Supply -CommunityPath explicitly."
    }
    if ($existingDirs.Count -eq 1) {
        return $existingDirs[0]
    }
    if ($existingDirs.Count -eq 0) {
        throw "Community folder not found. In FS2024, use Marketplace > My Library > Settings > Open, then pass -CommunityPath to this script."
    }
    throw "Multiple Community folders found. Supply -CommunityPath explicitly (do not guess)."
}

function Wait-ForCompiledPackage([string]$ExpectedVersion) {
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    $lastSignature = ""
    $stableObservations = 0

    while ($watch.Elapsed.TotalSeconds -lt 900) {
        $manifestPath = Join-Path $Compiled "manifest.json"
        $layoutPath = Join-Path $Compiled "layout.json"
        if ((Test-Path -LiteralPath $manifestPath) -and
            (Test-Path -LiteralPath $layoutPath)) {
            try {
                $manifest = Get-Content -LiteralPath $manifestPath -Raw |
                    ConvertFrom-Json
                $layout = Get-Content -LiteralPath $layoutPath -Raw |
                    ConvertFrom-Json
                $ktx = @(
                    Get-ChildItem -LiteralPath $Compiled -Filter "*.KTX2" -File -Recurse
                )
                $bgl = @(
                    Get-ChildItem -LiteralPath $Compiled -Filter "*.BGL" -File -Recurse
                )
                $glazed = @(
                    $ktx | Where-Object {
                        $_.Name -match '^WALL_.*_WIN_BASECOLOR\.PNG\.KTX2$'
                    }
                )
                $entries = @($layout.content)
                $correctVersion = ("$($manifest.package_version)" -eq $ExpectedVersion)
                $completeEnough = (
                    $correctVersion -and $ktx.Count -gt 20 -and
                    $bgl.Count -ge 2 -and $glazed.Count -gt 0 -and
                    $entries.Count -gt 20
                )

                if ($completeEnough) {
                    $files = @($ktx + $bgl) | Sort-Object FullName
                    $signature = (
                        ($files | ForEach-Object {
                            "$($_.Name):$($_.Length):$($_.LastWriteTimeUtc.Ticks)"
                        }) -join "|"
                    ) + "|$((Get-Item -LiteralPath $layoutPath).Length)"

                    if ($signature -eq $lastSignature) {
                        $stableObservations++
                    } else {
                        $stableObservations = 0
                        $lastSignature = $signature
                    }
                    if ($stableObservations -ge 4) {
                        Write-Host "SDK output stable: $($ktx.Count) KTX2, $($glazed.Count) glazed-wall textures, $($bgl.Count) BGL."
                        return
                    }
                } else {
                    $stableObservations = 0
                    $lastSignature = ""
                }
            } catch {
                # The SDK may be writing the JSON or KTX2 files right now.
                $stableObservations = 0
                $lastSignature = ""
            }
        }
        Start-Sleep -Seconds 3
    }
    throw "SDK build did not produce a stable v$ExpectedVersion package with BGL and window KTX2. Existing Community add-on was not replaced."
}

try {
    Step "Pre-flight"
    if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
        throw "Python virtual environment not found: $Python"
    }
    if (-not (Test-Path -LiteralPath $Sdk -PathType Leaf)) {
        throw "MSFS SDK package tool not found: $Sdk"
    }
    if (-not (Test-Path -LiteralPath $ProjectXml -PathType Leaf)) {
        throw "MSFS project XML not found: $ProjectXml"
    }
    if (-not (Test-Path -LiteralPath $PackageDefinition -PathType Leaf)) {
        throw "Package definition not found: $PackageDefinition"
    }

    $runningSim = @(Get-Process -Name @("FlightSimulator2024", "FlightSimulator") -ErrorAction SilentlyContinue)
    if ($runningSim.Count -gt 0) {
        throw "Close MSFS 2024 completely, then run this launcher again."
    }

    $community = Find-Community $CommunityPath
    Write-Host ("Active Community folder: " + $community) -ForegroundColor Green
    Push-Location $Root
    try {
        $versionXml = [xml](Get-Content -LiteralPath $PackageDefinition -Raw)
        $expectedVersion = [string]$versionXml.AssetPackage.Version
        Write-Host "Target package version: $expectedVersion"

        if (-not $SkipGitPull) {
            Step "Sync GitHub branch"
            $currentBranch = (& git branch --show-current)
            if ($LASTEXITCODE -ne 0) { throw "Could not read the Git branch" }
            if ($currentBranch.Trim() -ne $ExpectedBranch) {
                throw "Wrong Git branch: $currentBranch. Expected: $ExpectedBranch. Run 'git switch $ExpectedBranch' once."
            }
            & git pull --ff-only
            if ($LASTEXITCODE -ne 0) {
                throw "Git update failed. Local changes were not overwritten. Check 'git status'."
            }
            # The current script runs as loaded; get the package version again.
            $versionXml = [xml](Get-Content -LiteralPath $PackageDefinition -Raw)
            $expectedVersion = [string]$versionXml.AssetPackage.Version
        }

        Step "Verify Valmorel sources, PNG references, and windows"
        Run-Python "scripts\qa_bourg.py"

        Step "Generate 3D models and scenery placements"
        Run-Python "scripts\build_models.py"
        Run-Python "scripts\build_scenery.py"

        Step "Build with the official MSFS 2024 SDK"
        # Never reuse a previous build as evidence of success.
        # Dist and Community are NOT removed here.
        if (Test-Path -LiteralPath $Compiled) {
            Remove-Item -LiteralPath $Compiled -Recurse -Force
        }
        & $Sdk $ProjectXml
        if ($LASTEXITCODE -ne 0) {
            throw "SDK package tool returned exit code $LASTEXITCODE"
        }
        Write-Host "Waiting for generated BGL, layout and KTX2 files..."
        Wait-ForCompiledPackage $expectedVersion

        Step "Publish and validate the full package"
        Run-Python "scripts\publish_package.py"
        Run-Python "scripts\validate_package.py"
        $distManifest = Get-Content -LiteralPath (Join-Path $Dist "manifest.json") -Raw |
            ConvertFrom-Json
        if ("$($distManifest.package_version)" -ne $expectedVersion) {
            throw "Dist manifest version mismatch. Installation cancelled."
        }
        $compiledWindowKtx = @(
            Get-ChildItem -LiteralPath $Dist -Filter "*.KTX2" -File -Recurse |
                Where-Object {
                    $_.Name -match '^WALL_.*_WIN_BASECOLOR\.PNG\.KTX2$'
                }
        )
        if ($compiledWindowKtx.Count -eq 0) {
            throw "No compiled glazed facade texture found in dist. Installation cancelled."
        }

        Step "Back up old Community add-on and install the validated package"
        New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
        $target = Join-Path $community $PackageName
        $unique = [guid]::NewGuid().ToString("N").Substring(0, 8)
        $stage = Join-Path $community ("." + $PackageName + "_stage_" + $unique)
        $held = Join-Path $community ("." + $PackageName + "_old_" + $unique)
        if ((Test-Path -LiteralPath $stage) -or (Test-Path -LiteralPath $held)) {
            throw "Temporary staging location already exists. Installation cancelled."
        }

        # First prepare a complete replacement without touching installed files.
        Copy-Item -LiteralPath $Dist -Destination $stage -Recurse
        if (-not (Test-Path -LiteralPath (Join-Path $stage "manifest.json")) -or
            -not (Test-Path -LiteralPath (Join-Path $stage "layout.json"))) {
            throw "Community staging copy is incomplete."
        }

        if (Test-Path -LiteralPath $target) {
            $backup = Join-Path $BackupRoot (
                $PackageName + "_" + (Get-Date -Format "yyyyMMdd_HHmmss") + "_" + $unique
            )
            Copy-Item -LiteralPath $target -Destination $backup -Recurse
            if (-not (Test-Path -LiteralPath (Join-Path $backup "manifest.json"))) {
                throw "Backup incomplete. Existing installation was not touched."
            }
            Write-Host "Previous version backed up at: $backup"
            Move-Item -LiteralPath $target -Destination $held
            $previousMoved = $true
        }

        Move-Item -LiteralPath $stage -Destination $target
        $installationFinished = $true
        if (Test-Path -LiteralPath $held) {
            Remove-Item -LiteralPath $held -Recurse -Force
        }
        Step "SUCCESS"
        Write-Host "Valmorel HD v$expectedVersion installed in: $target" -ForegroundColor Green
        Write-Host "FS2024 can now be started. Keep the backup until checked in-game." -ForegroundColor Green
    } finally {
        Pop-Location
    }
} catch {
    Write-Host ""
    Write-Host ("ERROR: " + $_.Exception.Message) -ForegroundColor Red

    # If the previous package had been moved away, put it back.
    if ($previousMoved -and -not $installationFinished -and
        $null -ne $held -and (Test-Path -LiteralPath $held)) {
        try {
            $target = Join-Path $community $PackageName
            if (Test-Path -LiteralPath $target) {
                Remove-Item -LiteralPath $target -Recurse -Force
            }
            Move-Item -LiteralPath $held -Destination $target
            Write-Host "Previous Community version restored." -ForegroundColor Yellow
        } catch {
            Write-Host "ROLLBACK FAILED: old version is still at $held" -ForegroundColor Red
        }
    }

    if ($null -ne $stage -and (Test-Path -LiteralPath $stage)) {
        Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
    }
    Write-Host "No new version installed. See error above." -ForegroundColor Yellow
    exit 1
}
exit 0
