param(
    [Parameter(Mandatory)][string] $Fixture,
    [switch] $Baseline,
    [string] $SourceArchive = (Join-Path $env:DOTNET_ROOT 'library-packs/system.data.sqlclient.4.9.1.nupkg')
)
$ErrorActionPreference = 'Stop'
$implementation = [System.Data.SqlClient.SqlConnection].Assembly
$location = [IO.Path]::GetFullPath($implementation.Location)
if (!$location.StartsWith([IO.Path]::GetFullPath($PSHOME) + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'SqlClient must be loaded from the actual PowerShell bundle'
}
$archive = [IO.Compression.ZipFile]::OpenRead($SourceArchive)
try {
    $stream = $archive.GetEntry('runtimes/win/lib/net8.0/System.Data.SqlClient.dll').Open()
    $copy = [IO.MemoryStream]::new()
    try { $stream.CopyTo($copy); $expected = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($copy.ToArray())) }
    finally { $stream.Dispose(); $copy.Dispose() }
    $actual = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($location)))
    if ($actual -cne $expected) { throw 'Bundled SqlClient differs from the installed source archive' }
}
finally { $archive.Dispose() }
"SOURCE_SQLCLIENT $location SHA256 $actual"
"SOURCE_POWERSHELL $($PSVersionTable.PSVersion) $PSHOME"
"SOURCE_RUNTIME $([Runtime.InteropServices.RuntimeInformation]::FrameworkDescription)"
$assembly = [Reflection.Assembly]::LoadFrom([IO.Path]::GetFullPath($Fixture))
$method = $assembly.GetType('PowerShellBrowserChecks', $true).GetMethod('Run')
[string[]] $fixtureArguments = @()
if ($Baseline) { $fixtureArguments += '--baseline' }
[object[]] $arguments = @(,$fixtureArguments)
$result = $method.Invoke($null, $arguments)
if ($result -ne 0) { throw 'Bundled SQL Browser checks failed' }
'PASS original PowerShell bundled-source SqlClient SQL Browser named-instance/DAC queries and errors'
