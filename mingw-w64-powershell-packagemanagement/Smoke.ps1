param([string]$Manifest,[string]$ExpectedResources)
$ErrorActionPreference='Stop'
Import-Module $Manifest -Force -ErrorAction Stop
$module=Get-Module PackageManagement
if ($module.Version.ToString() -ne '1.4.8.1' -or $module.Guid.ToString() -ne '4ae9fd46-338a-459c-8186-07f910774cb8') { throw 'PackageManagement module identity mismatch' }
$root=Split-Path $Manifest
$binary=Join-Path $root coreclr/netstandard2.0
foreach ($name in 'Get-PackageProvider','Find-Package','Install-Package','Save-Package','Get-PackageSource','Register-PackageSource','Uninstall-Package') {
    $command=Get-Command $name -ErrorAction Stop
    if ($command.ImplementingType.Assembly.Location -ne (Join-Path $binary Microsoft.PowerShell.PackageManagement.dll)) { throw "foreign PackageManagement cmdlet $name" }
}
$provider=Import-PackageProvider -Name (Join-Path $binary Microsoft.PackageManagement.NuGetProvider.dll) -Force -ErrorAction Stop
if ($provider.Name -ne 'NuGet') { throw 'source NuGet provider did not load' }
if ([IO.Path]::GetFullPath($provider.ProviderPath) -ne [IO.Path]::GetFullPath((Join-Path $binary Microsoft.PackageManagement.NuGetProvider.dll))) { throw 'foreign NuGet provider' }
if ($ExpectedResources) {
    $expected=Get-Content -Raw -LiteralPath $ExpectedResources | ConvertFrom-Json -AsHashtable
    $count=0
    foreach ($name in $expected.Keys) {
        $assembly=[Reflection.Assembly]::LoadFrom((Join-Path $binary ($name+'.dll')))
        if ([IO.Path]::GetFullPath($assembly.Location) -ne [IO.Path]::GetFullPath((Join-Path $binary ($name+'.dll')))) { throw "foreign resource assembly $name" }
        foreach ($base in $expected[$name].Keys) {
            $manager=[Resources.ResourceManager]::new($base,$assembly)
            try {
                $set=$manager.GetResourceSet([Globalization.CultureInfo]::InvariantCulture,$true,$true)
                $actual=@{}
                foreach ($entry in $set.GetEnumerator()) { $actual[$entry.Key]=$entry.Value }
                $strings=$expected[$name][$base]
                if ($strings.Count -ne $actual.Count) { throw "resource inventory mismatch $name" }
                foreach ($key in $strings.Keys) {
                    if ($set.GetString($key) -cne $strings[$key]) { throw "resource mismatch $name/$key" }
                    $count++
                }
            } finally { $manager.ReleaseAllResources() }
        }
    }
    if ($count -ne 295) { throw 'PackageManagement resource count mismatch' }
    'PASS all295 original PackageManagement/NuGet resource values across five source assemblies'
}
'PASS source PackageManagement import/module/exports, original Core loader and source NuGet provider discovery'
