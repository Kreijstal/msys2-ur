$ErrorActionPreference = 'Stop'
$script:checks = 0
function Require([bool] $Value, [string] $Message) {
    $script:checks++
    if (!$Value) { throw $Message }
}
foreach ($identity in @(
    @{ Type = [Microsoft.Management.Infrastructure.CimSession]; Archive = 'microsoft.management.infrastructure.3.0.0.nupkg'; Asset = 'lib/net8.0/Microsoft.Management.Infrastructure.dll' },
    @{ Type = [System.Management.ManagementObject]; Archive = 'system.management.8.0.0.nupkg'; Asset = 'runtimes/win/lib/net8.0/System.Management.dll' }
)) {
    $dll = [IO.Path]::GetFullPath($identity.Type.Assembly.Location)
    Require ($dll.StartsWith([IO.Path]::GetFullPath($PSHOME) + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) 'Bundled source implementation loaded'
    $zip = [IO.Compression.ZipFile]::OpenRead((Join-Path $env:DOTNET_ROOT ('library-packs/' + $identity.Archive)))
    try {
        $stream = $zip.GetEntry($identity.Asset).Open()
        $copy = [IO.MemoryStream]::new()
        try {
            $stream.CopyTo($copy)
            Require ([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($copy.ToArray())) -ceq [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($dll)))) 'Bundled implementation matches installed source archive'
        }
        finally { $stream.Dispose(); $copy.Dispose() }
    }
    finally { $zip.Dispose() }
}

$name = 'MSYS2_WmiPersist_' + [Guid]::NewGuid().ToString('N')
$root = [System.Management.ManagementScope]::new('root')
$root.Connect()
$namespacePath = '__Namespace.Name="' + $name + '"'
$created = $false
try {
    $namespaceType = [System.Management.ManagementClass]::new($root, [System.Management.ManagementPath]::new('__Namespace'), $null)
    try {
        $namespace = $namespaceType.CreateInstance()
        try {
            $namespace['Name'] = $name
            $options = [System.Management.PutOptions]::new()
            $options.Type = [System.Management.PutType]::CreateOnly
            $null = $namespace.Put($options)
            $created = $true
        }
        finally { $namespace.Dispose() }
    }
    finally { $namespaceType.Dispose() }
    $scope = [System.Management.ManagementScope]::new('root\' + $name)
    $scope.Connect()
    $type = [System.Management.ManagementClass]::new($scope, [System.Management.ManagementPath]::new(), $null)
    try {
        $type['__CLASS'] = 'MSYS2_PowerShellRecord'
        $type.Properties.Add('Id', [System.Management.CimType]::String, $false)
        $type.Properties['Id'].Qualifiers.Add('Key', $true)
        $type.Properties.Add('Text', [System.Management.CimType]::String, $false)
        $type.Properties.Add('Counter', [System.Management.CimType]::UInt32, $false)
        $null = $type.Put()
        foreach ($dcom in @($false, $true)) {
            $session = $null
            $instance = $null
            try {
                $arguments = @{ Namespace = ('root/' + $name); ClassName = 'MSYS2_PowerShellRecord' }
                if ($dcom) {
                    $session = New-CimSession -SessionOption (New-CimSessionOption -Protocol Dcom)
                    $arguments.CimSession = $session
                }
                $instance = New-CimInstance @arguments -Property @{ Id = 'owned'; Text = 'created 雪 π'; Counter = [uint32]7 }
                Require ($instance.Id -ceq 'owned' -and $instance.Text -ceq 'created 雪 π' -and $instance.Counter -eq 7) 'Original New-CimInstance returns persisted values'
                $stored = [System.Management.ManagementObject]::new($scope, [System.Management.ManagementPath]::new('MSYS2_PowerShellRecord.Id="owned"'), $null)
                try { $stored.Get(); Require ([string]$stored['Text'] -ceq 'created 雪 π') 'Source WMI reads original CIM cmdlet write' }
                finally { $stored.Dispose() }
                $operation = @{}
                if ($null -ne $session) { $operation.CimSession = $session }
                Set-CimInstance @operation -InputObject $instance -Property @{ Text = 'updated Ω'; Counter = [uint32]42 }
                $rows = @(Get-CimInstance @arguments)
                try {
                    Require ($rows.Count -eq 1 -and $rows[0].Text -ceq 'updated Ω' -and $rows[0].Counter -eq 42) 'Original Set/Get-CimInstance persist and query updated values'
                    Remove-CimInstance @operation -InputObject $rows[0]
                }
                finally { foreach ($row in $rows) { $row.Dispose() } }
                Require (@(Get-CimInstance @arguments).Count -eq 0) 'Original Remove-CimInstance deletes repository row'
                [GC]::Collect(2, [GCCollectionMode]::Forced, $true, $true)
            }
            finally {
                if ($null -ne $instance) { $instance.Dispose() }
                if ($null -ne $session) { Remove-CimSession $session }
            }
        }
        $type.Delete()
    }
    finally { $type.Dispose() }
    $modules = [Diagnostics.Process]::GetCurrentProcess().Modules
    Require (@($modules | Where-Object ModuleName -eq 'msys-wmi-native.dll').Count -eq 1) 'Source native WMI helper loaded'
    Require (@($modules | Where-Object { $_.ModuleName -eq 'wminet_utils.dll' -or $_.FileName -match '\\Microsoft.NET\\Framework' }).Count -eq 0) 'No Framework helper loaded'
}
finally {
    if ($created) {
        $namespace = [System.Management.ManagementObject]::new($root, [System.Management.ManagementPath]::new($namespacePath), $null)
        try { $namespace.Delete(); "REMOVED $name" }
        finally { $namespace.Dispose() }
    }
}
"PASS $script:checks original PowerShell default/DCOM CIM repository writes and source WMI interoperability checks"
