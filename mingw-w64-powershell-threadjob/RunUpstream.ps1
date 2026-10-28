param([string]$PesterManifest,[string]$ThreadJobManifest,[string]$TestScript,[string]$OutputDirectory)
$ErrorActionPreference='Stop'
Import-Module $PesterManifest -Force -ErrorAction Stop
Import-Module $ThreadJobManifest -Force -ErrorAction Stop
$module=Get-Module ThreadJob
if ($module.Version.ToString() -ne '2.0.3' -or $module.Guid.ToString() -ne '0e7b895d-2fec-43f7-8cae-11e8d16f6e40') { throw 'ThreadJob module identity mismatch' }
if (($module.ExportedCmdlets.Keys -join ',') -ne 'Start-ThreadJob') { throw 'ThreadJob exported cmdlet mismatch' }
$assembly=(Get-Command Start-ThreadJob).ImplementingType.Assembly
if ($assembly.Location -ne (Join-Path (Split-Path $ThreadJobManifest) Microsoft.PowerShell.ThreadJob.dll)) { throw 'foreign ThreadJob implementation' }
if ($assembly.GetName().Version.ToString() -ne '2.0.1.0') { throw 'ThreadJob frozen assembly version mismatch' }
if (Test-Path variable:global:OwnedThreadJobCheck) { throw 'owned ThreadJob fixture already exists' }
$global:OwnedThreadJobCheck=@{Manifest=$ThreadJobManifest;Output=$OutputDirectory;HostDll=(Join-Path ([AppContext]::BaseDirectory) SourcePowerShell.ModuleHost.dll)}
function global:Invoke-OwnedThreadJobChild([string]$Script) {
    $file=Join-Path $global:OwnedThreadJobCheck.Output (([guid]::NewGuid().ToString())+'.ps1')
    $manifest=$global:OwnedThreadJobCheck.Manifest.Replace("'","''")
    $content="Import-Module '$manifest' -ErrorAction Stop`n"+$Script
    [IO.File]::WriteAllText($file,$content,[Text.UTF8Encoding]::new($false))
    try {
        $exe=Join-Path $env:DOTNET_ROOT dotnet.exe
        & $exe $global:OwnedThreadJobCheck.HostDll $file
        if ($LASTEXITCODE -ne 0) { throw "ThreadJob child host exited $LASTEXITCODE" }
    } finally { Remove-Item -LiteralPath $file -Force }
}
try {
    # The original interactive-host tests expect ordinary nonterminating errors.
    $ErrorActionPreference='Continue'
    $result=Invoke-Pester -Script $TestScript -PassThru -Show Failed,Summary
    $ErrorActionPreference='Stop'
    $record=$result | Select-Object TotalCount,PassedCount,FailedCount,SkippedCount,PendingCount,InconclusiveCount
    $record | Add-Member -NotePropertyName TestResult -NotePropertyValue @($result.TestResult | Select-Object Describe,Context,Name,Result,Passed,FailureMessage,StackTrace,Time)
    $record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $OutputDirectory results.json)
    if ($result.TotalCount -ne 30 -or $result.PassedCount -ne 30 -or $result.FailedCount -ne 0 -or $result.SkippedCount -ne 0 -or $result.PendingCount -ne 0 -or $result.InconclusiveCount -ne 0) { throw "original ThreadJob suite: $($result.PassedCount) passed, $($result.FailedCount) failed" }
    'PASS all30 original ThreadJob cases, including fresh-process runspace cleanup'
} finally {
    Remove-Item function:global:Invoke-OwnedThreadJobChild -ErrorAction SilentlyContinue
    Remove-Variable OwnedThreadJobCheck -Scope Global -ErrorAction SilentlyContinue
}
