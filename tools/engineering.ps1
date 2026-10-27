# Shared local workflow launcher; the state store lives beside the backend runner.
$ErrorActionPreference = 'Stop'
$taskRepoRoot = Split-Path -Parent $PSScriptRoot
$taskFlowRoot = Join-Path $PSScriptRoot 'engineering_flow'
if (-not (Test-Path -LiteralPath (Join-Path $taskFlowRoot 'flow.py'))) {
  $taskPlatformRoot = Split-Path -Parent $taskRepoRoot
  $taskFlowRoot = Join-Path $taskPlatformRoot 'kavehmetal back/tg1/tools/engineering_flow'
}
if (-not (Test-Path -LiteralPath (Join-Path $taskFlowRoot 'flow.py'))) {
  throw 'Backend engineering runner not found. Open the companion backend checkout or use its absolute path.'
}
$taskUv = Get-Command uv -ErrorAction SilentlyContinue
if ($taskUv) { $taskUvPath = $taskUv.Source }
else { $taskUvPath = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.local/bin/uv.exe' }
if (-not (Test-Path -LiteralPath $taskUvPath)) { throw 'uv is missing; install it and run uv sync for tools/engineering_flow.' }
& $taskUvPath run --frozen --offline --project $taskFlowRoot python -X utf8 (Join-Path $taskFlowRoot 'flow.py') @args
exit $LASTEXITCODE
