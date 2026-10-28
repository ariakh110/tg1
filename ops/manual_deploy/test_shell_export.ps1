$ErrorActionPreference = "Stop"
$scriptPath = Join-Path $PSScriptRoot "deploy.ps1"
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw "deploy.ps1 parse errors" }
$function = $ast.Find({
  param($node)
  $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq "Export-LfShellScript"
}, $true)
if (-not $function) { throw "Missing Export-LfShellScript export boundary" }
Invoke-Expression $function.Extent.Text
$tempRoot = [System.IO.Path]::GetTempPath()
$caseDir = Join-Path $tempRoot ("kaveh-shell-export-" + [guid]::NewGuid().ToString("N"))
[void][System.IO.Directory]::CreateDirectory($caseDir)
$source = Join-Path $caseDir "source.sh"
$destination = Join-Path $caseDir "output.sh"
try {
  $unicode = [string][char]0x06A9
  $expected = "#!/usr/bin/env bash" + "`n# " + $unicode + "`nset -euo pipefail`n"
  $fixture = $expected.Replace("`n", "`r`n")
  [System.IO.File]::WriteAllText($source, $fixture, (New-Object System.Text.UTF8Encoding($true)))
  Export-LfShellScript -Source $source -Destination $destination
  $bytes = [System.IO.File]::ReadAllBytes($destination)
  if ([Array]::IndexOf($bytes, [byte]13) -ge 0) { throw "CR found in exported shell file" }
  if ($bytes[0] -ne 35 -or $bytes[1] -ne 33) { throw "BOM or missing shebang" }
  if ([System.IO.File]::ReadAllText($destination) -cne $expected) { throw "UTF-8 content changed" }
  Export-LfShellScript -Source $destination -Destination $source
  if ([System.IO.File]::ReadAllText($source) -cne $expected) { throw "LF roundtrip changed" }
  Write-Output "PASS: CRLF/BOM normalized, Unicode preserved, LF roundtrip stable."
}
finally {
  foreach ($file in @($source, $destination)) {
    if (Test-Path -LiteralPath $file) { Remove-Item -LiteralPath $file }
  }
  Remove-Item -LiteralPath $caseDir
}
