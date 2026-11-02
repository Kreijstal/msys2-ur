param([string]$Manifest)
$ErrorActionPreference='Stop'
Import-Module $Manifest -Force -ErrorAction Stop
$command=Get-Command Start-ThreadJob -ErrorAction Stop
$assembly=$command.ImplementingType.Assembly
if ($assembly.GetName().Version.ToString() -ne '2.0.1.0') { throw 'ThreadJob frozen assembly version mismatch' }
$job=Start-ThreadJob { Get-Location; Write-Output 'Owned thread job' }
try {
    $null=$job|Wait-Job -Timeout 10
    if ($job.State -ne 'Completed') { throw "job state $($job.State): $($job.JobStateInfo.Reason); errors=$($job.Error -join ';')" }
    $result=@($job|Receive-Job -ErrorAction Stop)
    if ($result.Count -ne 2 -or $result[1] -ne 'Owned thread job') { throw 'thread job output mismatch' }
    'PASS source ThreadJob import, identity, stock command discovery, execution, wait/receive and removal'
} finally { $job|Remove-Job -Force }
