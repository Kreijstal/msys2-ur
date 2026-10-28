$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.ToString() -ne '7.4.20') { throw 'source engine version mismatch' }
if ($env:SOURCE_POWERSHELL_TEST_CULTURE -and $PSUICulture -ne $env:SOURCE_POWERSHELL_TEST_CULTURE) { throw 'source test host culture mismatch' }
foreach ($name in 'Add-Type', 'Import-LocalizedData', 'Get-Item', 'New-Item', 'Out-File', 'Get-FileHash') {
    $command = Get-Command $name -ErrorAction Stop
    if (-not $command.ImplementingType.Assembly.Location.StartsWith([AppContext]::BaseDirectory)) { throw "foreign implementation $name" }
}
$compiled = Add-Type -TypeDefinition 'public static class OwnedCompile { public static int Value() => 42; }' -PassThru
if ($compiled::Value() -ne 42) { throw 'source Add-Type compiler failed' }
$previousModulePath = $env:PSModulePath
$env:PSModulePath = Join-Path ([AppContext]::BaseDirectory) Modules
$child = [PowerShell]::Create()
$child.Runspace = [System.Management.Automation.Runspaces.RunspaceFactory]::CreateRunspace(
    [System.Management.Automation.Runspaces.InitialSessionState]::CreateDefault2())
try {
    $child.Runspace.Open()
    $null = $child.AddScript(@'
        $ErrorActionPreference = 'Stop'
        $null = Get-Location
        $null = Write-Output 'owned child'
        $null = Get-ExecutionPolicy
        $os = Get-CimInstance -ClassName Win32_OperatingSystem
        if (-not $os.BuildNumber) { throw 'child CIM query failed' }
        foreach ($name in 'Get-Location','Write-Output','Get-ExecutionPolicy','Get-CimInstance') {
            $command = Get-Command $name -ListImported
            if (-not $command.ImplementingType.Assembly.Location.StartsWith([AppContext]::BaseDirectory)) {
                throw "foreign child implementation $name"
            }
        }
        'PASS child runspace autoloads all four original source modules'
'@)
    $result = $child.Invoke()
    if ($child.HadErrors -or $child.InvocationStateInfo.State -ne 'Completed' -or $result.Count -ne 1) {
        throw "child module discovery failed: $($child.Streams.Error); $($child.InvocationStateInfo.Reason)"
    }
    $result
} finally {
    $child.Runspace.Dispose()
    $child.Dispose()
    $env:PSModulePath = $previousModulePath
}
'PASS source PowerShell engine, original Utility/Management/Security/CIM cmdlet modules and Add-Type compiler'
