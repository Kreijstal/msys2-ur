$ErrorActionPreference='Stop'
$parent=[Environment]::ProcessId
$job=Start-Job -ScriptBlock {
    $ErrorActionPreference='Stop'
    Import-Module Microsoft.PowerShell.Management,Microsoft.PowerShell.Utility,CimCmdlets
    [pscustomobject]@{
        Pid=[Environment]::ProcessId
        Value='λ original source child'
        Engine=[System.Management.Automation.PowerShell].Assembly.Location
        Console=[Microsoft.PowerShell.UnmanagedPSEntry].Assembly.Location
        Build=(Get-CimInstance Win32_OperatingSystem).BuildNumber
        Framework=@([AppDomain]::CurrentDomain.GetAssemblies() | Where-Object { $_.Location -match '[\\/]Microsoft.NET[\\/]Framework' }).Count
    }
}
try {
    $null=Wait-Job $job -Timeout 90
    if ($job.State -ne 'Completed') { throw "source child failed: $($job.State); $($job.ChildJobs[0].JobStateInfo.Reason)" }
    $result=Receive-Job $job -ErrorAction Stop
    if ($result.Pid -eq $parent -or $result.Value -cne 'λ original source child' -or -not $result.Build -or $result.Framework -ne 0) { throw 'source child behavior mismatch' }
    foreach ($name in 'Engine','Console') {
        if ([IO.Path]::GetDirectoryName($result.$name) -ne $PSHOME) { throw "foreign child assembly $name = $($result.$name)" }
    }
    'PASS original console entry/native apphost Start-Job process, Unicode CLIXML, source engine/ConsoleHost, module discovery, live CIM query and no Framework implementations'
} finally { Remove-Job $job -Force }
