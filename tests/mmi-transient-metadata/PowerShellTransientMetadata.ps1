param(
    [Parameter(Mandatory)][string] $Fixture,
    [Parameter(Mandatory)][string] $Driver,
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
$method = $assembly.GetType('PowerShellTransientMetadataChecks', $true).GetMethod('Run')
[string[]] $fixtureArguments = @('--driver=' + [IO.Path]::GetFullPath($Driver))
if ($Baseline) { $fixtureArguments += '--baseline' }
[object[]] $arguments = @(,$fixtureArguments)
$result = $method.Invoke($null, $arguments)
if ($result -ne 0) { throw 'Bundled transient metadata checks failed' }
'PASS original PowerShell bundled-source MMI transient metadata/deletion/metadata/GC/cache and source identity'
