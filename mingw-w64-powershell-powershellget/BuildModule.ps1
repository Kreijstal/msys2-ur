param([string]$SourceRoot,[string]$OwnedDirectory)
$ErrorActionPreference='Stop'
foreach ($name in 'APPDATA','LOCALAPPDATA','ProgramFiles','ProgramData') {
    [Environment]::SetEnvironmentVariable($name,(Join-Path $OwnedDirectory $name),'Process')
}
$dist=Join-Path $SourceRoot dist
if (Test-Path -LiteralPath $dist) { throw 'PowerShellGet output directory must be new' }
$null=New-Item -Path $dist -ItemType Directory
Copy-Item -LiteralPath (Join-Path $SourceRoot src/PowerShellGet) -Destination $dist -Recurse
$module=Join-Path $dist PowerShellGet
Remove-Item -LiteralPath (Join-Path $module public),(Join-Path $module private) -Recurse -Force
Remove-Item -LiteralPath (Join-Path $module PSModule.psm1) -Force
Import-Module (Join-Path $SourceRoot tools/build.psm1) -Force -ErrorAction Stop
# Original assembly function only. Dependency/bootstrap/publish tasks are not invoked.
New-ModulePSMFile
'PASS original PowerShellGet module assembly function completed'
