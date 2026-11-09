param([string] $SourceArchive = (Join-Path $env:DOTNET_ROOT 'library-packs/microsoft.management.infrastructure.3.0.0.nupkg'))
$ErrorActionPreference = 'Stop'
$script:checks = 0
function Require([bool] $Value, [string] $Message) {
    $script:checks++
    if (!$Value) { throw $Message }
}
function Read-Value([Microsoft.Management.Infrastructure.CimProperty] $Property) {
    # A normal PowerShell property read can hide a CLR getter exception.
    $value = $Property.GetType().GetProperty('Value').GetValue($Property)
    return ,$value
}
function Write-Value([Microsoft.Management.Infrastructure.CimProperty] $Property, [object] $Value) {
    $Property.GetType().GetProperty('Value').SetValue($Property, $Value)
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

foreach ($kind in @('Instance','Reference','InstanceArray','ReferenceArray')) {
    $child = [Microsoft.Management.Infrastructure.CimInstance]::new('MSYS2_AppChild', 'root/cimv2')
    $parent = [Microsoft.Management.Infrastructure.CimInstance]::new('MSYS2_AppParent')
    $first = $null; $second = $null
    try {
        $child.CimInstanceProperties.Add([Microsoft.Management.Infrastructure.CimProperty]::Create('Id', [uint32]42, [Microsoft.Management.Infrastructure.CimType]::UInt32, [Microsoft.Management.Infrastructure.CimFlags]::Key))
        $child.CimInstanceProperties.Add([Microsoft.Management.Infrastructure.CimProperty]::Create('Label', 'PowerShell 雪 λ', [Microsoft.Management.Infrastructure.CimType]::String, [Microsoft.Management.Infrastructure.CimFlags]::None))
        $array = $kind.EndsWith('Array')
        $inputValue = $child
        if ($array) { $inputValue = [Microsoft.Management.Infrastructure.CimInstance[]]@($child) }
        $parent.CimInstanceProperties.Add([Microsoft.Management.Infrastructure.CimProperty]::Create('Child', $inputValue, [Microsoft.Management.Infrastructure.CimType]$kind, [Microsoft.Management.Infrastructure.CimFlags]::None))
        $property = $parent.CimInstanceProperties['Child']
        $first = Read-Value $property; $second = Read-Value $property
        if ($array) { $first = $first[0]; $second = $second[0] }
        Require (![object]::ReferenceEquals($first, $second)) "Independent nested results: $kind"
        Write-Value $first.CimInstanceProperties['Label'] 'mutated'
        Require ((Read-Value $second.CimInstanceProperties['Label']) -ceq 'PowerShell 雪 λ') "Mutation isolation: $kind"
        $first.Dispose(); $first = $null
        $property.IsValueModified = $false
        Require (!$property.IsValueModified) "Fresh modification flag false: $kind"
        $property.IsValueModified = $true
        Require ($property.IsValueModified) "Fresh modification flag true: $kind"
        $parent.Dispose(); $child.Dispose()
        [GC]::Collect(2, [GCCollectionMode]::Forced, $true, $true); [GC]::WaitForPendingFinalizers()
        Require ((Read-Value $second.CimInstanceProperties['Label']) -ceq 'PowerShell 雪 λ') "Nested result outlives parent/source and GC: $kind"
    }
    finally {
        if ($null -ne $first) { $first.Dispose() }
        if ($null -ne $second) { $second.Dispose() }
        $parent.Dispose(); $child.Dispose()
    }
}

$owner = [Microsoft.Management.Infrastructure.CimInstance]::new('MSYS2_AppArrays')
try {
    $owner.CimInstanceProperties.Add([Microsoft.Management.Infrastructure.CimProperty]::Create('Numbers', [int[]]@(1,2,3), [Microsoft.Management.Infrastructure.CimType]::SInt32Array, [Microsoft.Management.Infrastructure.CimFlags]::None))
    $property = $owner.CimInstanceProperties['Numbers']
    $values = Read-Value $property; $values[0] = 99
    Require ((Read-Value $property)[0] -eq 1) 'Primitive array snapshot isolation'
    Write-Value $owner.CimInstanceProperties['Numbers'] ([int[]]@(4,5))
    Require ((Read-Value $property)[0] -eq 4) 'Held property sees updates through another wrapper'
    Write-Value $property ([int[]]@())
    $empty = Read-Value $property
    Require ($empty -is [int[]] -and $empty.Length -eq 0) 'Typed empty array preserved'
    Write-Value $property $null
    Require ($null -eq (Read-Value $property)) 'NULL array remains distinct from empty'
}
finally { $owner.Dispose() }

$session = $null; $subscription = $null; $outer = $null; $target = $null
$children = [Collections.Generic.List[Diagnostics.Process]]::new()
$identifier = 'MSYS2_EmbeddedEvent_' + [Guid]::NewGuid().ToString('N')
try {
    $session = New-CimSession -SessionOption (New-CimSessionOption -Protocol Dcom)
    Require ($null -ne $session) 'Original New-CimSession cmdlet creates local DCOM session'
    $query = "SELECT * FROM __InstanceCreationEvent WITHIN 1 WHERE TargetInstance ISA 'Win32_Process' AND TargetInstance.ParentProcessId=$PID"
    $subscription = Register-CimIndicationEvent -CimSession $session -Namespace root/cimv2 -Query $query -SourceIdentifier $identifier
    $notification = $null; $watch = [Diagnostics.Stopwatch]::StartNew()
    while ($null -eq $notification -and $watch.Elapsed.TotalSeconds -lt 20) {
        $start = [Diagnostics.ProcessStartInfo]::new($env:ComSpec, '/d /c ping -n 12 127.0.0.1 >nul')
        $start.UseShellExecute = $false; $start.CreateNoWindow = $true
        $children.Add([Diagnostics.Process]::Start($start))
        $notification = Wait-Event -SourceIdentifier $identifier -Timeout 2
    }
    Require ($null -ne $notification) 'Original Register-CimIndicationEvent delivers a real intrinsic event'
    $outer = $notification.SourceEventArgs.NewEvent
    Require ($outer -is [Microsoft.Management.Infrastructure.CimInstance]) 'Original event exposes a CIM instance'
    $target = Read-Value $outer.CimInstanceProperties['TargetInstance']
    Require ($target -is [Microsoft.Management.Infrastructure.CimInstance]) 'Embedded event target is a CIM instance'
    Unregister-Event -SourceIdentifier $identifier
    $subscription = $null
    Remove-Event -SourceIdentifier $identifier
    Remove-CimSession -CimSession $session; $session = $null
    $outer.Dispose(); $outer = $null
    [GC]::Collect(2, [GCCollectionMode]::Forced, $true, $true); [GC]::WaitForPendingFinalizers()
    $eventPid = [int](Read-Value $target.CimInstanceProperties['ProcessId'])
    Require ($children.Id -contains $eventPid) 'Retained TargetInstance identifies an owned child'
    Require ((Read-Value $target.CimInstanceProperties['ParentProcessId']) -eq $PID) 'Retained TargetInstance identifies this PowerShell parent'
    Require ((Read-Value $target.CimInstanceProperties['Name']) -ieq 'cmd.exe') 'Retained event payload survives subscription/session/outer-event disposal and GC'
}
finally {
    if ($null -ne $subscription) { Unregister-Event -SourceIdentifier $identifier -ErrorAction SilentlyContinue }
    Get-Event -SourceIdentifier $identifier -ErrorAction SilentlyContinue | Remove-Event -ErrorAction SilentlyContinue
    if ($null -ne $target) { $target.Dispose() }
    if ($null -ne $outer) { $outer.Dispose() }
    if ($null -ne $session) { Remove-CimSession -CimSession $session }
    foreach ($child in $children) {
        try { if (!$child.HasExited) { $child.Kill($true) }; [void]$child.WaitForExit(5000) }
        finally { $child.Dispose() }
    }
}
Write-Output "PASS $script:checks PowerShell embedded/reference/array/flags/lifetime and real intrinsic CIM event checks"
