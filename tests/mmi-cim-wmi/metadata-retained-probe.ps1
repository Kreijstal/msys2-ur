$ErrorActionPreference='Stop'
function New-HeldDeclaration {
    $class=Get-CimClass -Namespace root/cimv2 -ClassName Win32_Process
    return ,@($class.CimClassProperties['ProcessId'],[WeakReference]::new($class))
}
$values=New-HeldDeclaration
[GC]::Collect(2,[GCCollectionMode]::Forced,$true,$true);[GC]::WaitForPendingFinalizers()
[GC]::Collect(2,[GCCollectionMode]::Forced,$true,$true);[GC]::WaitForPendingFinalizers()
"ParentAlive=$($values[1].IsAlive)"
"Assembly=$([Microsoft.Management.Infrastructure.CimClass].Assembly.Location)"
try { "PropertyName=$($values[0].GetType().GetProperty('Name').GetValue($values[0]))" }
catch { "PropertyError=$($_.Exception.ToString())";exit 1 }
