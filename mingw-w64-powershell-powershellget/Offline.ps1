param([string]$Manifest,[string]$PackageManagementManifest,[string]$OwnedDirectory)
$ErrorActionPreference='Stop'
foreach ($name in 'APPDATA','LOCALAPPDATA','ProgramFiles','ProgramData') {
    [Environment]::SetEnvironmentVariable($name,(Join-Path $OwnedDirectory $name),'Process')
}
$documents=[Environment]::GetFolderPath('MyDocuments')
$dirs=@((Join-Path $documents PowerShell),(Join-Path $documents PowerShell/Scripts),(Join-Path $documents PowerShell/Scripts/InstalledScriptInfos))
$new=@($dirs | Where-Object { -not (Test-Path -LiteralPath $_) })
$userScript=Join-Path $documents PowerShell/Scripts/Owned.Script.ps1
$userScriptInfo=Join-Path $documents PowerShell/Scripts/InstalledScriptInfos/Owned.Script_InstalledScriptInfo.xml
if ((Test-Path $userScript) -or (Test-Path $userScriptInfo)) { throw 'CurrentUser fixture script name is already in use' }
$createdUserScript=$false
$repository='OwnedSource'
try {
    Import-Module $PackageManagementManifest -Force
    $binary=Join-Path (Split-Path $PackageManagementManifest) coreclr/netstandard2.0
    $provider=Import-PackageProvider -Name (Join-Path $binary Microsoft.PackageManagement.NuGetProvider.dll) -Force
    if ([IO.Path]::GetFullPath($provider.ProviderPath) -ne [IO.Path]::GetFullPath((Join-Path $binary Microsoft.PackageManagement.NuGetProvider.dll))) { throw 'foreign NuGet provider' }
    Import-Module $Manifest -Force
    $psprovider=Get-PackageProvider -Name PowerShellGet
    if ([IO.Path]::GetFullPath($psprovider.ProviderPath) -ne [IO.Path]::GetFullPath((Join-Path (Split-Path $Manifest) PSModule.psm1))) { throw 'foreign PowerShellGet provider implementation' }
    $feed=Join-Path $OwnedDirectory feed
    Register-PSRepository -Name $repository -SourceLocation $feed -PublishLocation $feed -ScriptSourceLocation $feed -ScriptPublishLocation $feed -InstallationPolicy Trusted
    $repo=Get-PSRepository -Name $repository
    if (-not $repo -or -not $repo.SourceLocation) { throw "repository missing: $($repo | Out-String); providers=$(Get-PackageProvider | Out-String); sources=$(Get-PackageSource | Out-String)" }
    if ([IO.Path]::GetFullPath($repo.SourceLocation) -ne [IO.Path]::GetFullPath($feed) -or $repo.InstallationPolicy -ne 'Trusted') { throw "repository persistence failed $($repo | ConvertTo-Json -Compress)" }
    # Original 2.2.5 compares a locally synthesized Boolean IsPrerelease against
    # the string 'false'. Its local -AllVersions stable filter therefore drops
    # these packages; preserve and check that upstream behavior explicitly.
    $stableAll=@(Find-Module -Name Owned.Module -Repository $repository -AllVersions)
    if ($stableAll.Count -ne 0) { throw 'original local stable AllVersions behavior changed' }
    $found=@(Find-Module -Name Owned.Module -Repository $repository -AllVersions -AllowPrerelease)
    if ($found.Count -ne 2 -or [version]'1.1.0' -notin $found.Version) {
        $raw=@(PackageManagement\Find-Package -Name Owned.Module -AllVersions -Source $feed -ProviderName NuGet -FilterOnTag PSModule)
        throw "module discovery failed count=$($found.Count); raw=$($raw | Out-String); errors=$($global:Error | Out-String)"
    }
    $saved=Join-Path $OwnedDirectory saved
    $null=New-Item -ItemType Directory $saved
    Save-Module -Name Owned.Module -RequiredVersion 1.0.0 -Repository $repository -Path $saved -Force
    foreach ($name in 'Owned.Module','Owned.Dependency') {
        if (-not (Test-Path (Join-Path $saved "$name/1.0.0/$name.psd1"))) { throw "saved dependency/module missing $name" }
    }
    Install-Module -Name Owned.Module -RequiredVersion 1.0.0 -Repository $repository -Scope AllUsers -Force -Confirm:$false -Verbose -Debug 4> (Join-Path $OwnedDirectory install-verbose.log) 5> (Join-Path $OwnedDirectory install-debug.log)
    $installed=Get-InstalledModule -Name Owned.Module -RequiredVersion 1.0.0
    $expected=Join-Path $env:ProgramFiles PowerShell/Modules/Owned.Module/1.0.0
    if (-not $installed) { throw "installed module missing; ProgramFiles=$env:ProgramFiles; expected=$expected; errors=$($global:Error | Out-String)" }
    if ([IO.Path]::GetFullPath($installed.InstalledLocation) -ne [IO.Path]::GetFullPath($expected)) { throw "install escaped owned directory $($installed.InstalledLocation)" }
    Import-Module (Join-Path $expected Owned.Module.psd1) -Force
    if ((Get-OwnedValue) -cne 'Owned.Module 1.0.0 λ owned') { throw 'installed module payload mismatch' }
    Remove-Module Owned.Module,Owned.Dependency
    Update-Module -Name Owned.Module -RequiredVersion 1.1.0 -Scope AllUsers -Force -Confirm:$false
    $updated=Get-InstalledModule -Name Owned.Module -RequiredVersion 1.1.0
    if ($updated.Version -ne [version]'1.1.0' -or [IO.Path]::GetFullPath($updated.InstalledLocation) -ne [IO.Path]::GetFullPath((Join-Path $env:ProgramFiles PowerShell/Modules/Owned.Module/1.1.0))) { throw 'module update failed or escaped owned directory' }
    Uninstall-Module -Name Owned.Module -AllVersions -Force -Confirm:$false
    Remove-Module Owned.Dependency -Force -ErrorAction SilentlyContinue
    Uninstall-Module -Name Owned.Dependency -Force -Confirm:$false
    if (Get-ChildItem (Join-Path $env:ProgramFiles PowerShell/Modules) -Filter '*.psm1' -Recurse) { throw "owned uninstall left implementation files; errors=$($global:Error | Out-String)" }
    'PASS source PowerShellGet repository persistence, find, dependency save/install, installed Unicode module execution, update and uninstall'
    $scriptFile=Join-Path $OwnedDirectory Local.Script.ps1
    New-ScriptFileInfo -Path $scriptFile -Version 1.0.0 -Author 'Owned fixture' -Description 'Owned metadata round trip'
    if ((Test-ScriptFileInfo -Path $scriptFile).Version -ne '1.0.0') { throw 'script metadata creation failed' }
    Update-ScriptFileInfo -Path $scriptFile -Version 1.1.0 -Description 'Owned updated metadata'
    if ((Test-ScriptFileInfo -Path $scriptFile).Version -ne '1.1.0') { throw 'script metadata update failed' }
    $scriptInfo=Find-Script -Name Owned.Script -RequiredVersion 1.0.0 -Repository $repository
    if ($scriptInfo.Name -ne 'Owned.Script' -or $scriptInfo.Version -ne '1.0.0') { throw 'script discovery failed' }
    $savedScripts=Join-Path $OwnedDirectory saved-scripts
    $null=New-Item -ItemType Directory $savedScripts
    Save-Script -Name Owned.Script -RequiredVersion 1.0.0 -Repository $repository -Path $savedScripts -Force
    if ((& (Join-Path $savedScripts Owned.Script.ps1)) -cne 'Owned.Script 1.0.0 λ owned') { throw 'saved script payload mismatch' }
    Install-Script -Name Owned.Script -RequiredVersion 1.0.0 -Repository $repository -Scope AllUsers -NoPathUpdate -Force -Confirm:$false
    $installedScript=Get-InstalledScript -Name Owned.Script
    $scriptsPath=Join-Path $env:ProgramFiles PowerShell/Scripts
    if ([IO.Path]::GetFullPath($installedScript.InstalledLocation) -ne [IO.Path]::GetFullPath($scriptsPath)) { throw 'script escaped owned installation directory' }
    if ((& (Join-Path $scriptsPath Owned.Script.ps1)) -cne 'Owned.Script 1.0.0 λ owned') { throw 'installed script payload mismatch' }
    # Original Core Update-Script deliberately moves an AllUsers script into
    # CurrentUser and exposes no Scope parameter. Own these two initially absent
    # fixture files explicitly, then verify and remove them even on failure.
    $createdUserScript=$true
    Update-Script -Name Owned.Script -RequiredVersion 1.1.0 -Force -Confirm:$false
    if ((Get-InstalledScript -Name Owned.Script).Version -ne '1.1.0') { throw 'script update failed' }
    if ((& $userScript) -cne 'Owned.Script 1.1.0 λ owned') { throw 'updated script payload mismatch' }
    Uninstall-Script -Name Owned.Script -Force -Confirm:$false
    if ((Test-Path (Join-Path $scriptsPath Owned.Script.ps1)) -or (Test-Path $userScript)) { throw 'script uninstall left payload' }
    'PASS source PowerShellGet script metadata create/update/parse, discovery, save, owned install/execution, update and uninstall'
} catch {
    throw "offline PowerShellGet check failed at $($_.ScriptStackTrace): $($_.Exception.Message)"
} finally {
    if ($createdUserScript) {
        if (Test-Path -LiteralPath $userScript) {
            if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($userScript)) -cne [Convert]::ToBase64String([IO.File]::ReadAllBytes((Join-Path $OwnedDirectory script-1.1.0.expected.ps1)))) { throw 'unexpected CurrentUser fixture script bytes; preserving file' }
            Remove-Item -LiteralPath $userScript -Force
        }
        if (Test-Path -LiteralPath $userScriptInfo) {
            $info=[System.Management.Automation.PSSerializer]::Deserialize([IO.File]::ReadAllText($userScriptInfo))
            if ($info.Name -ne 'Owned.Script' -or [IO.Path]::GetFullPath($info.RepositorySourceLocation) -ne [IO.Path]::GetFullPath($feed)) { throw 'unexpected CurrentUser fixture metadata; preserving file' }
            Remove-Item -LiteralPath $userScriptInfo -Force
        }
    }
    if (Get-Command Unregister-PSRepository -ErrorAction SilentlyContinue) { Unregister-PSRepository -Name $repository -ErrorAction SilentlyContinue }
    Remove-Module PowerShellGet -ErrorAction SilentlyContinue
    [array]::Reverse($new)
    foreach ($path in $new) {
        if ((Test-Path -LiteralPath $path) -and @(Get-ChildItem -LiteralPath $path -Force).Count -eq 0) { Remove-Item -LiteralPath $path -Force }
    }
}
