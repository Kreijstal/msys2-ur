param([string]$Manifest,[string]$PackageManagementManifest,[string]$OwnedDirectory)
$ErrorActionPreference='Stop'
foreach ($name in 'APPDATA','LOCALAPPDATA','ProgramFiles','ProgramData') {
    [Environment]::SetEnvironmentVariable($name,(Join-Path $OwnedDirectory $name),'Process')
}
# The original import creates empty CurrentUser script-info directories. Remove
# only directories newly created by this check, only while they remain empty.
$documents=[Environment]::GetFolderPath('MyDocuments')
$dirs=@((Join-Path $documents PowerShell),(Join-Path $documents PowerShell/Scripts),(Join-Path $documents PowerShell/Scripts/InstalledScriptInfos))
$new=@($dirs | Where-Object { -not (Test-Path -LiteralPath $_) })
try {
    Import-Module $PackageManagementManifest -Force -ErrorAction Stop
    Import-Module $Manifest -Force -ErrorAction Stop
    $module=Get-Module PowerShellGet
    if ($module.Version.ToString() -ne '2.2.5' -or $module.Guid.ToString() -ne '1d73a601-4a6c-43c5-ba3f-619b18bbb404') { throw 'PowerShellGet module identity mismatch' }
    $data=Import-PowerShellDataFile -LiteralPath $Manifest
    if ((($module.ExportedFunctions.Keys | Sort-Object) -join ',') -ne (($data.FunctionsToExport | Sort-Object) -join ',')) { throw 'PowerShellGet exported functions mismatch' }
    foreach ($name in $module.ExportedFunctions.Keys) {
        if ((Get-Command $name).ScriptBlock.File -ne (Join-Path (Split-Path $Manifest) PSModule.psm1)) { throw "foreign PowerShellGet implementation $name" }
    }
    'PASS exact source PowerShellGet2.2.5 import and all exported functions against installed source PackageManagement'
} finally {
    Remove-Module PowerShellGet -ErrorAction SilentlyContinue
    [array]::Reverse($new)
    foreach ($path in $new) {
        if ((Test-Path -LiteralPath $path) -and @(Get-ChildItem -LiteralPath $path -Force).Count -eq 0) { Remove-Item -LiteralPath $path -Force }
    }
}
