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
$type = $assembly.GetType('PowerShellSessionOptionChecks', $true)
$type.GetProperty('DriverPath').SetValue($null, (Join-Path ([IO.Path]::GetDirectoryName($Fixture)) '../../../session-options-native.dll'))
$method = $type.GetMethod('Run')
[string[]] $fixtureArguments = @()
if ($Baseline) { $fixtureArguments += '--baseline' }
[object[]] $arguments = @(,$fixtureArguments)
$result = $method.Invoke($null, $arguments)
if ($result -ne 0) { throw 'Bundled session option/native wrapper checks failed' }
$mismatches = 0
foreach ($spn in @($false, $true)) {
    foreach ($revocation in @($false, $true)) {
        $parameters = @{ EncodePortInServicePrincipalName = $spn }
        if (!$revocation) { $parameters.SkipRevocationCheck = $true }
        $options = New-CimSessionOption @parameters
        try {
            if ($options.CertRevocationCheck -ne $revocation) { throw 'New-CimSessionOption revocation control failed' }
            if ($options.EncodePortInServicePrincipalName -ne $spn) { $mismatches++ }
        }
        finally { $options.Dispose() }
    }
}
if (($Baseline -and $mismatches -ne 2) -or (!$Baseline -and $mismatches -ne 0)) { throw "Unexpected cmdlet SPN mismatches: $mismatches" }
"PASS four original New-CimSessionOption SPN/revocation combinations; mismatches=$mismatches baseline=$Baseline"
'PASS original PowerShell bundled-source MMI session options and source identity'
