param(
    [Parameter(Mandatory)][string] $Fixture,
    [switch] $Baseline,
    [string] $SourceArchive = (Join-Path $env:DOTNET_ROOT 'library-packs/microsoft.management.infrastructure.3.0.0.nupkg')
)
$ErrorActionPreference = 'Stop'
$implementation = [Microsoft.Management.Infrastructure.CimInstance].Assembly
$location = [IO.Path]::GetFullPath($implementation.Location)
if (!$location.StartsWith([IO.Path]::GetFullPath($PSHOME) + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'MMI must be loaded from the actual PowerShell bundle'
}
$archive = [IO.Compression.ZipFile]::OpenRead($SourceArchive)
try {
    $stream = $archive.GetEntry('lib/net8.0/Microsoft.Management.Infrastructure.dll').Open()
    $copy = [IO.MemoryStream]::new()
    try { $stream.CopyTo($copy); $expected = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($copy.ToArray())) }
    finally { $stream.Dispose(); $copy.Dispose() }
    $actual = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($location)))
    if ($actual -cne $expected) { throw 'Bundled MMI differs from the installed source archive' }
}
finally { $archive.Dispose() }
"SOURCE_MMI $location SHA256 $actual"
"SOURCE_POWERSHELL $($PSVersionTable.PSVersion) $PSHOME"
"SOURCE_RUNTIME $([Runtime.InteropServices.RuntimeInformation]::FrameworkDescription)"
$assembly = [Reflection.Assembly]::LoadFrom([IO.Path]::GetFullPath($Fixture))
$method = $assembly.GetType('PowerShellQualifierLookupChecks', $true).GetMethod('Run')
[string[]] $fixtureArguments = @()
if ($Baseline) { $fixtureArguments += '--baseline' }
[object[]] $arguments = @(,$fixtureArguments)
$result = $method.Invoke($null, $arguments)
if ($result -ne 0) { throw 'Bundled method qualifier lookup checks failed' }
if (!$Baseline) {
    $class = Get-CimClass -ClassName Win32_Process -Namespace root/cimv2 -ErrorAction Stop
    try {
        $count = 0
        foreach ($method in $class.CimClassMethods) {
            foreach ($qualifier in $method.Qualifiers) {
                $found = $method.Qualifiers.get_Item($qualifier.Name)
                if ($null -eq $found -or $found.Name -cne $qualifier.Name -or $found.CimType -ne $qualifier.CimType -or $found.Flags -ne $qualifier.Flags -or
                    ![Collections.StructuralComparisons]::StructuralEqualityComparer.Equals($found.Value, $qualifier.Value)) {
                    throw "Get-CimClass method qualifier lookup disagrees with enumeration: $($method.Name)/$($qualifier.Name)"
                }
                $count++
            }
        }
        if ($count -lt 1) { throw 'Get-CimClass exposed no method qualifiers' }
        "PASS $count original Get-CimClass named method qualifiers with values/types/flags"
    }
    finally { $class.Dispose() }
}
'PASS original PowerShell bundled-source MMI method qualifier lookup and source identity'
