param([string]$Manifest,[string]$OwnedDirectory)
$ErrorActionPreference='Stop'
Import-Module $Manifest -Force -ErrorAction Stop
$binary=Join-Path (Split-Path $Manifest) coreclr/netstandard2.0
$null=Import-PackageProvider -Name (Join-Path $binary Microsoft.PackageManagement.NuGetProvider.dll) -Force -ErrorAction Stop
$feed=Join-Path $OwnedDirectory feed
$config=Join-Path $OwnedDirectory NuGet.Config
$destination=Join-Path $OwnedDirectory installed
$source=Register-PackageSource -Name OwnedSource -Location $feed -ProviderName NuGet -Trusted -Force -ConfigFile $config
if ($source.Name -ne 'OwnedSource') { throw 'owned source registration failed' }
try {
    $registered=Get-PackageSource -Name OwnedSource -ProviderName NuGet -ConfigFile $config
    if ([IO.Path]::GetFullPath($registered.Location) -ne [IO.Path]::GetFullPath($feed)) { throw 'owned source persistence mismatch' }
    $found=@(Find-Package -Name Owned.Root -MinimumVersion 1.0.0 -Source $feed -ProviderName NuGet -ConfigFile $config)
    if ($found.Count -ne 1 -or $found[0].Version -ne '1.0.0') { throw "stable local package discovery failed: count=$($found.Count); items=$($found | Select-Object Name,Version,Source | ConvertTo-Json -Compress)" }
    # Original local-feed behavior includes prereleases under -AllVersions.
    $all=@(Find-Package -Name Owned.Root -AllVersions -Source $feed -ProviderName NuGet -ConfigFile $config)
    if ($all.Count -ne 2 -or '1.1.0-preview.1' -notin $all.Version) { throw 'original local all-versions behavior mismatch' }
    $prerelease=@(Find-Package -Name Owned.Root -AllVersions -AllowPrereleaseVersions -Source $feed -ProviderName NuGet -ConfigFile $config)
    if ($prerelease.Count -ne 2 -or '1.1.0-preview.1' -notin $prerelease.Version) { throw 'prerelease local package discovery failed' }
    $saved=@(Save-Package -Name Owned.Root -RequiredVersion 1.0.0 -Source $feed -ProviderName NuGet -Path (Join-Path $OwnedDirectory saved) -Force -ConfigFile $config)
    if ('Owned.Root' -notin $saved.Name -or 'Owned.Dependency' -notin $saved.Name) { throw 'local save/dependency resolution failed' }
    $installed=@(Install-Package -Name Owned.Root -RequiredVersion 1.0.0 -Source $feed -ProviderName NuGet -Destination $destination -Force -ConfigFile $config)
    if ('Owned.Root' -notin $installed.Name -or 'Owned.Dependency' -notin $installed.Name) { throw 'local install/dependency resolution failed' }
    $payloads=@(Get-ChildItem -LiteralPath $destination -Filter payload.txt -Recurse)
    if ($payloads.Count -ne 2) { throw 'local install payload inventory failed' }
    foreach ($payload in $payloads) {
        $text=Get-Content -Raw -LiteralPath $payload.FullName
        if ($text -notmatch '^Owned\.(Root|Dependency) 1\.0\.0 λ owned') { throw 'local install payload bytes mismatch' }
    }
    $inventory=@(Get-Package -ProviderName NuGet -Destination $destination)
    if ('Owned.Root' -notin $inventory.Name -or 'Owned.Dependency' -notin $inventory.Name) { throw 'local installed package inventory failed' }
    $null=$inventory | Uninstall-Package -Force -Destination $destination
    if (Get-ChildItem -LiteralPath $destination -Filter payload.txt -Recurse) { throw 'owned uninstall left package payloads' }
    'PASS source PackageManagement/NuGet local source registration, stable/prerelease find, dependency save/install, Unicode extraction, inventory and uninstall'
} catch {
    throw "owned offline check failed at $($_.ScriptStackTrace): $($_.Exception.Message)"
} finally {
    $null=Unregister-PackageSource -Name OwnedSource -ProviderName NuGet -Force -ConfigFile $config
}
