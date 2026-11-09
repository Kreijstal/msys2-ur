param([string]$Fixture, [string]$Root, [string]$Graph, [string]$Result)
$ErrorActionPreference = 'Stop'
$null = [Reflection.Assembly]::LoadFrom($Fixture)
$json = [CompatibilityIntegration]::Run($Root, $Graph)
[IO.File]::WriteAllText($Result, $json)
$record = $json | ConvertFrom-Json
Write-Output "PASS original PowerShell $($PSVersionTable.PSVersion) $($record.apartment): $($record.assertions) cross-library assertions"
