# Build committed release archives and optionally upload/apply them.
# Usage:
#   .\deploy.ps1
#   .\deploy.ps1 frontend
#   .\deploy.ps1 frontend -PrepareOnly

[CmdletBinding()]
param(
  [ValidateSet("both", "backend", "frontend")]
  [string]$Target = "both",
  [switch]$PrepareOnly
)

$ErrorActionPreference = "Stop"

$server = "root@130.185.75.68"
$deployDir = "C:\Users\ariakh\deploy"
$beRepo = "C:\Users\ariakh\DEV\PY\tg1"
$feRepo = "C:\Users\ariakh\DEV\JS\kavehmetal"
$branch = "dev-ariakhayer"
$canonicalUpdater = Join-Path $beRepo "ops\manual_deploy\update.sh"

function Assert-NativeCommand {
  param(
    [Parameter(Mandatory = $true)][string]$Operation,
    [Parameter(Mandatory = $true)][int]$ExitCode
  )

  if ($ExitCode -ne 0) {
    throw "$Operation failed with exit code $ExitCode"
  }
}

function Write-ArchiveHash {
  param([Parameter(Mandatory = $true)][string]$Path)

  $hash = (Get-FileHash $Path -Algorithm SHA256).Hash
  Write-Host "==> $([System.IO.Path]::GetFileName($Path)) SHA256: $hash" -ForegroundColor DarkGray
}

if (-not (Test-Path -LiteralPath $canonicalUpdater -PathType Leaf)) {
  throw "Canonical updater is missing: $canonicalUpdater"
}

New-Item -ItemType Directory -Force $deployDir | Out-Null
Copy-Item -LiteralPath $canonicalUpdater -Destination "$deployDir\update.sh" -Force
$files = @()

if ($Target -eq "backend" -or $Target -eq "both") {
  Write-Host "==> Building backend archive from $branch..." -ForegroundColor Cyan
  git -C $beRepo archive --format=tar.gz -o "$deployDir\backend.tar.gz" $branch
  Assert-NativeCommand "Backend git archive" $LASTEXITCODE
  Write-ArchiveHash "$deployDir\backend.tar.gz"
  $files += "$deployDir\backend.tar.gz"
}

if ($Target -eq "frontend" -or $Target -eq "both") {
  Write-Host "==> Building frontend archive from $branch..." -ForegroundColor Cyan
  git -C $feRepo archive --format=tar.gz -o "$deployDir\frontend.tar.gz" $branch
  Assert-NativeCommand "Frontend git archive" $LASTEXITCODE

  $requiredFrontendEntries = @(
    "package.json",
    "package-lock.json",
    "ops/deploy_frontend_release.sh"
  )
  $frontendArchiveEntries = @(tar -tzf "$deployDir\frontend.tar.gz")
  Assert-NativeCommand "Frontend archive inspection" $LASTEXITCODE
  $missingFrontendEntries = @(
    $requiredFrontendEntries | Where-Object { $_ -notin $frontendArchiveEntries }
  )
  if ($missingFrontendEntries.Count -gt 0) {
    throw "Frontend archive is incomplete. Missing: $($missingFrontendEntries -join ', ')"
  }

  Write-ArchiveHash "$deployDir\frontend.tar.gz"
  $files += "$deployDir\frontend.tar.gz"
}

$files += "$deployDir\update.sh"

if ($PrepareOnly) {
  Write-Host "==> Release files prepared in $deployDir; no server connection was made." -ForegroundColor Green
  $files | ForEach-Object { Write-Host "    $_" }
  return
}

Write-Host "==> Uploading release files..." -ForegroundColor Cyan
scp $files "${server}:/opt/tirexa/"
Assert-NativeCommand "Release upload" $LASTEXITCODE

Write-Host "==> Applying release on the server..." -ForegroundColor Cyan
ssh $server "bash /opt/tirexa/update.sh $Target"
Assert-NativeCommand "Remote deployment" $LASTEXITCODE

Write-Host "==> Deployment complete: https://kavex.ir" -ForegroundColor Green
