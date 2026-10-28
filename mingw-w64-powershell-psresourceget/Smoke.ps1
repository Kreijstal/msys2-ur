param([string]$ModuleManifest,[string]$OwnedRoot)
$ErrorActionPreference='Stop'
try {
function Require([bool]$Condition,[string]$Message){if(-not $Condition){throw $Message}}
Import-Module $ModuleManifest -Force -ErrorAction Stop
$module=Get-Module Microsoft.PowerShell.PSResourceGet
Require ($module.Version -eq [version]'1.1.1') 'original module version'
Require ($module.ExportedCmdlets.Count -eq 17) 'all17 original cmdlets exported'
Require ($module.ExportedFunctions.ContainsKey('Import-PSGetRepository')) 'original script module nested/exported'
$command=Get-Command 'Microsoft.PowerShell.PSResourceGet\Find-PSResource'
$assembly=$command.ImplementingType.Assembly
Require ($assembly.GetName().Version.ToString() -eq '1.1.0.1') 'frozen source assembly version'
Require ($assembly.Location -eq (Join-Path (Split-Path $ModuleManifest) 'Microsoft.PowerShell.PSResourceGet.dll')) 'owned source module loaded'
Add-Type -Path (Join-Path $PSScriptRoot 'OwnedVersionPort.cs')
Import-Module ([OwnedPSResourceVersionPort].Assembly)
Test-OwnedPSResourceVersionPort -ErrorAction Stop
New-Item -ItemType Directory -Path $OwnedRoot -ErrorAction Stop | Out-Null
$path=Join-Path $OwnedRoot 'OwnedScript.ps1'
$guid=[guid]'11111111-2222-3333-4444-555555555555'
Microsoft.PowerShell.PSResourceGet\New-PSScriptFileInfo -Path $path -Version '1.2.3' -Author 'owned author' -Description 'owned λ script' -Guid $guid
$info=Microsoft.PowerShell.PSResourceGet\Get-PSScriptFileInfo -Path $path
Require ($info.ScriptMetadataComment.Version.ToString() -eq '1.2.3' -and $info.ScriptMetadataComment.Author -eq 'owned author') 'new/get script metadata'
Microsoft.PowerShell.PSResourceGet\Test-PSScriptFileInfo -Path $path -ErrorAction Stop | Out-Null
Microsoft.PowerShell.PSResourceGet\Update-PSScriptFileInfo -Path $path -Version '1.2.4' -Description 'updated owned λ script'
$info=Microsoft.PowerShell.PSResourceGet\Get-PSScriptFileInfo -Path $path
Require ($info.ScriptMetadataComment.Version.ToString() -eq '1.2.4' -and $info.ScriptMetadataComment.Guid -eq $guid) 'update/reopen script metadata'
# A dependency is exercised through the module's original private loading path.
$loaded=[AppDomain]::CurrentDomain.GetAssemblies() | Where-Object { $_.GetName().Name -like 'NuGet.*' }
Require ($loaded.Count -gt 0) 'original NuGet dependency resolution used'
$payloads=Get-Content (Join-Path (Split-Path $ModuleManifest) 'source-dependencies.json') -Raw | ConvertFrom-Json -AsHashtable
foreach($dependency in $loaded){
    Require ($dependency.Location.StartsWith((Join-Path (Split-Path $ModuleManifest) 'dependencies'),[StringComparison]::OrdinalIgnoreCase)) 'NuGet loaded from owned private source dependencies'
    $file=Split-Path $dependency.Location -Leaf
    Require ((Get-FileHash $dependency.Location -Algorithm SHA256).Hash.ToLowerInvariant() -eq $payloads[$file].sha256) 'loaded private NuGet implementation bytes match source inventory'
}
Write-Output 'PASS original full manifest/module initializer,17cmdlet exports/nested module, source engine import and new/get/test/update script metadata with private source NuGet dependencies'

} catch { [Console]::Error.WriteLine($_.InvocationInfo.PositionMessage); [Console]::Error.WriteLine($_.ScriptStackTrace); [Console]::Error.WriteLine($_.Exception.ToString()); throw }
