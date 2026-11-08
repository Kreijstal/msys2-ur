param([string] $SourceArchive = (Join-Path $env:DOTNET_ROOT 'library-packs/microsoft.management.infrastructure.3.0.0.nupkg'))
$ErrorActionPreference = 'Stop'
$script:checks = 0
function Require([bool] $Value, [string] $Message) {
    $script:checks++
    if (!$Value) { throw $Message }
}

# This bridge supplies a typed CLR delegate to the native parser. It uses no
# private MMI API and avoids PowerShell runspace requirements in native callbacks.
Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Threading;
public static class PowerShellMofIncludeFixture {
    public static int Calls;
    public static byte[] Include(string name) {
        if (name != "schema-雪.mof") throw new InvalidOperationException("Unexpected include filename: " + name);
        Interlocked.Increment(ref Calls);
        GC.Collect(2, GCCollectionMode.Forced, true, true);
        string text = "class MSYS2_PowerShellMof { uint32 Id; string Label; };\n";
        byte[] payload = Encoding.Unicode.GetBytes(text);
        byte[] bom = Encoding.Unicode.GetPreamble();
        byte[] result = new byte[bom.Length + payload.Length];
        Buffer.BlockCopy(bom, 0, result, 0, bom.Length);
        Buffer.BlockCopy(payload, 0, result, bom.Length, payload.Length);
        return result;
    }
}
'@

$assembly = [Microsoft.Management.Infrastructure.CimSession].Assembly
$dll = [IO.Path]::GetFullPath($assembly.Location)
Require ($dll.StartsWith([IO.Path]::GetFullPath($PSHOME) + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) 'PowerShell must load its bundled MMI implementation'
Require ($assembly.GetName().Version -eq [version]'1.0.0.0') 'MMI assembly identity'
$archive = [IO.Compression.ZipFile]::OpenRead($SourceArchive)
try {
    $entry = $archive.GetEntry('lib/net8.0/Microsoft.Management.Infrastructure.dll')
    Require ($null -ne $entry) 'Source package implementation asset'
    $stream = $entry.Open()
    $copy = [IO.MemoryStream]::new()
    try { $stream.CopyTo($copy); $expected = [Security.Cryptography.SHA256]::HashData($copy.ToArray()) }
    finally { $stream.Dispose(); $copy.Dispose() }
    $actual = [Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($dll))
    Require ([Convert]::ToHexString($actual) -ceq [Convert]::ToHexString($expected)) 'Bundled MMI bytes must match the installed source package'
}
finally { $archive.Dispose() }

$type = $assembly.GetType('Microsoft.Management.Infrastructure.Serialization.CimMofDeserializer', $true)
$includeType = $type.GetNestedType('GetIncludedFileContent', [Reflection.BindingFlags]'Public,NonPublic')
$include = [Delegate]::CreateDelegate($includeType, [PowerShellMofIncludeFixture].GetMethod('Include'))
$create = $type.GetMethod('Create', [Reflection.BindingFlags]'Public,Static')
$deserialize = @($type.GetMethods() | Where-Object { $_.Name -eq 'DeserializeInstances' -and $_.GetParameters().Length -eq 4 })
Require ($deserialize.Count -eq 1) 'Internal MOF callback entrypoint is unambiguous'
$reader = $create.Invoke($null, [object[]]@())
$rows = @()
try {
    $text = "#pragma include (`"schema-雪.mof`")`ninstance of MSYS2_PowerShellMof { Id=42; Label=`"PowerShell 雪 λ`"; };`n"
    [byte[]] $bytes = @([byte]0xa5) * 5 + [Text.Encoding]::Unicode.GetPreamble() + [Text.Encoding]::Unicode.GetBytes($text)
    [object[]] $arguments = @($bytes, [uint32]5, $null, $include)
    $rows = @($deserialize[0].Invoke($reader, $arguments))
    Require ([PowerShellMofIncludeFixture]::Calls -eq 1) 'Native parser invoked the Unicode include callback'
    Require ($arguments[1] -eq $bytes.Length) 'Nonzero MOF input offset advanced by the consumed length'
    Require ($rows.Count -eq 1) 'One MOF instance returned to PowerShell'
    $reader.Dispose()
    [GC]::Collect(2, [GCCollectionMode]::Forced, $true, $true)
    Require ($rows[0].CimSystemProperties.ClassName -ceq 'MSYS2_PowerShellMof') 'MOF class survived parser disposal and GC'
    Require ($rows[0].CimInstanceProperties['Id'].Value -eq 42) 'MOF integer payload'
    Require ($rows[0].CimInstanceProperties['Label'].Value -ceq 'PowerShell 雪 λ') 'MOF Unicode payload'
}
finally {
    foreach ($row in $rows) { $row.Dispose() }
    $reader.Dispose()
}

$os = Get-CimInstance -ClassName Win32_OperatingSystem
try { Require (![string]::IsNullOrEmpty($os.Version)) 'Live CIM cmdlet after MOF parser cleanup' }
finally { $os.Dispose() }
$process = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$PID"
try { Require ($process.ProcessId -eq $PID) 'Live CIM query identifies this PowerShell process' }
finally { $process.Dispose() }
Write-Output "PASS $script:checks PowerShell bundled-source MMI/MOF/Unicode/include/offset/lifetime/live-CIM checks"
