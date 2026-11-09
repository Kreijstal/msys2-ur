param([string] $SourceArchive = (Join-Path $env:DOTNET_ROOT 'library-packs/microsoft.management.infrastructure.3.0.0.nupkg'))
$ErrorActionPreference = 'Stop'
$script:checks = 0
function Require([bool] $Value, [string] $Message) {
    $script:checks++
    if (!$Value) { throw $Message }
}
$assembly = [Microsoft.Management.Infrastructure.CimSession].Assembly
$dll = [IO.Path]::GetFullPath($assembly.Location)
Require ($dll.StartsWith([IO.Path]::GetFullPath($PSHOME) + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) 'PowerShell loads its bundled MMI'
$archive = [IO.Compression.ZipFile]::OpenRead($SourceArchive)
try {
    $entry = $archive.GetEntry('lib/net8.0/Microsoft.Management.Infrastructure.dll')
    Require ($null -ne $entry) 'Source archive implementation asset'
    $stream = $entry.Open(); $copy = [IO.MemoryStream]::new()
    try { $stream.CopyTo($copy); $expected = [Security.Cryptography.SHA256]::HashData($copy.ToArray()) }
    finally { $stream.Dispose(); $copy.Dispose() }
    $actual = [Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($dll))
    Require ([Convert]::ToHexString($actual) -ceq [Convert]::ToHexString($expected)) 'Bundled MMI matches installed source package bytes'
}
finally { $archive.Dispose() }

function Read-Metadata([object] $Value, [string] $Name) {
    # Invoke the CLR getter directly so PowerShell cannot hide its exception.
    return ,$Value.GetType().GetProperty($Name).GetValue($Value)
}
function Check-Qualifiers([object] $Values) {
    foreach ($qualifier in $Values) {
        Require (![string]::IsNullOrEmpty((Read-Metadata $qualifier 'Name'))) 'Qualifier name'
        $null = Read-Metadata $qualifier 'Value'
        $null = Read-Metadata $qualifier 'CimType'
        $null = Read-Metadata $qualifier 'Flags'
        [GC]::Collect(2, [GCCollectionMode]::Forced, $true, $true)
    }
}
for ($iteration=0; $iteration -lt 4; $iteration++) {
    $class = Get-CimClass -Namespace root/cimv2 -ClassName Win32_Process -ErrorAction Stop
    try {
        Require ($class.CimSystemProperties.ClassName -ceq 'Win32_Process') 'Original Get-CimClass returned live process metadata'
        Require ($class.CimClassQualifiers.Count -gt 0) 'Class qualifier count'
        Check-Qualifiers $class.CimClassQualifiers
        foreach ($property in $class.CimClassProperties) {
            $name = Read-Metadata $property 'Name'
            Require ($null -ne $class.CimClassProperties[$name]) 'Property name lookup'
            $null = Read-Metadata $property 'Value'
            $null = Read-Metadata $property 'CimType'
            $null = Read-Metadata $property 'Flags'
            Check-Qualifiers $property.Qualifiers
        }
        foreach ($method in $class.CimClassMethods) {
            $name = Read-Metadata $method 'Name'
            Require ($null -ne $class.CimClassMethods[$name]) 'Method name lookup'
            Require ((Read-Metadata $method 'ReturnType') -eq [Microsoft.Management.Infrastructure.CimType]::UInt32) 'Process method return type'
            Check-Qualifiers $method.Qualifiers
            foreach ($parameter in $method.Parameters) {
                $name = Read-Metadata $parameter 'Name'
                Require ($null -ne $method.Parameters[$name]) 'Parameter name lookup'
                $null = Read-Metadata $parameter 'CimType'
                $null = Read-Metadata $parameter 'ReferenceClassName'
                Check-Qualifiers $parameter.Qualifiers
            }
        }
        [GC]::Collect(2, [GCCollectionMode]::Forced, $true, $true)
        [GC]::WaitForPendingFinalizers()
        Require ($class.CimClassMethods['Create'].Parameters['CommandLine'].CimType -eq [Microsoft.Management.Infrastructure.CimType]::String) 'Live class remains intact after metadata view cleanup'
    }
    finally { $class.Dispose() }
}
"PASS $script:checks PowerShell original Get-CimClass qualifier/parameter metadata and GC checks"
