param([string]$Manifest)
$ErrorActionPreference='Stop'
Import-Module $Manifest -Force -ErrorAction Stop
$gate=[System.Threading.ManualResetEventSlim]::new($false)
$hits=[System.Collections.Concurrent.ConcurrentQueue[int]]::new()
$job=$null
$breakpoint=$null
try {
    $action={ $hits.Enqueue(42) }.GetNewClosure()
    $breakpoint=Set-PSBreakpoint -Command OwnedThreadJobDebugProbe -Action $action
    $job=Start-ThreadJob -ScriptBlock {
        $signal=$using:gate
        while (-not $signal.IsSet) { Start-Sleep -Milliseconds 10 }
        function OwnedThreadJobDebugProbe { 'owned debug body' }
        OwnedThreadJobDebugProbe
    }
    $deadline=[DateTime]::UtcNow.AddSeconds(10)
    while ($job.State -eq 'NotStarted' -and [DateTime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 10 }
    if ($job.State -ne 'Running') { throw "debug job failed to start: $($job.State)" }
    # The current engine's one-argument method must dispatch to our adapted
    # two-argument override and then to the real child runspace's debugger.
    $job.Debugger.SetDebugMode([System.Management.Automation.DebugModes]::LocalScript)
    $job.Debugger.SetBreakpoints([System.Management.Automation.Breakpoint[]]@($breakpoint))
    $gate.Set()
    $null=$job | Wait-Job -Timeout 10
    if ($job.State -ne 'Completed') { throw "debug job failed: $($job.State); $($job.JobStateInfo.Reason)" }
    $result=@($job | Receive-Job -ErrorAction Stop)
    [int]$value=0
    if ($result.Count -ne 1 -or $result[0] -ne 'owned debug body' -or $breakpoint.HitCount -ne 1 -or -not $hits.TryDequeue([ref]$value) -or $value -ne 42 -or $hits.Count -ne 0) { throw "breakpoint forwarding failed: $result; hits=$($breakpoint.HitCount)" }
    'PASS debugger overload adapter forwards a real child command breakpoint and invokes its action exactly once'
} finally {
    $gate.Set()
    if ($null -ne $job) { $job | Remove-Job -Force }
    if ($null -ne $breakpoint) { $breakpoint | Remove-PSBreakpoint }
    $gate.Dispose()
}
