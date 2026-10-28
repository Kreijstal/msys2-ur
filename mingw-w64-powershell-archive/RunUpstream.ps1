param([string]$PesterManifest, [string]$ArchiveManifest, [string]$TestScript, [string]$ResultPath, [string]$Culture = 'en-GB')
$ErrorActionPreference = 'Stop'
if ($PSUICulture -ne $Culture) { throw "test host UI culture mismatch: $PSUICulture versus $Culture" }
[System.Threading.Thread]::CurrentThread.CurrentCulture = [System.Globalization.CultureInfo]::GetCultureInfo($Culture)
[System.Threading.Thread]::CurrentThread.CurrentUICulture = [System.Globalization.CultureInfo]::GetCultureInfo($Culture)
Import-Module $PesterManifest -Force -ErrorAction Stop
Import-Module $ArchiveManifest -Force -ErrorAction Stop
$module = Get-Module Microsoft.PowerShell.Archive
if ($module.Version.ToString() -ne '1.2.6') { throw 'archive module identity mismatch' }
if ($module.Guid.ToString() -ne 'eb74e8da-9ae2-482a-a648-e96550fb8733') { throw 'archive module GUID mismatch' }
if ((($module.ExportedFunctions.Keys | Sort-Object) -join ',') -ne 'Compress-Archive,Expand-Archive') { throw 'archive exported function surface mismatch' }
$expectedScript = Join-Path (Split-Path $ArchiveManifest) 'Microsoft.PowerShell.Archive.psm1'
foreach ($name in 'Compress-Archive','Expand-Archive') {
    if ((Get-Command $name).ScriptBlock.File -ne $expectedScript) { throw "unexpected module implementation for $name" }
}
$result = Invoke-Pester -Script $TestScript -PassThru -Show Failed,Summary
$record = $result | Select-Object TotalCount,PassedCount,FailedCount,SkippedCount,PendingCount,InconclusiveCount
$record | Add-Member -NotePropertyName TestResult -NotePropertyValue @($result.TestResult | Select-Object Describe,Context,Name,Result,Passed,FailureMessage,StackTrace,Time)
$record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ResultPath
if ($result.TotalCount -ne 99 -or $result.PassedCount -ne 98 -or $result.FailedCount -ne 0 -or $result.SkippedCount -ne 0 -or $result.PendingCount -ne 1 -or $result.InconclusiveCount -ne 0) { throw "original archive suite failed: $($result.FailedCount) failed, $($result.PassedCount) passed" }
'PASS original archive suite against the exact explicitly imported module: ' + $result.PassedCount + ' passed, ' + $result.SkippedCount + ' skipped, ' + $result.PendingCount + ' pending'
