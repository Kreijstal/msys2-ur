$ErrorActionPreference = 'Stop'
$class = Get-CimClass -Namespace root/cimv2 -ClassName Win32_Process -ErrorAction Stop
try {
    $method = $class.CimClassMethods.get_Item('Create')
    $qualifier = @($method.Qualifiers)[0]
    if ($null -eq $qualifier) { throw 'Baseline provider has no Create method qualifiers' }
    $named = $method.Qualifiers.get_Item($qualifier.Name)
    if ($null -ne $named) { throw 'Baseline unexpectedly resolved the requested method qualifier' }
    "REPRODUCED original Get-CimClass: Create/$($qualifier.Name) enumerates but named lookup returns null"
    "SOURCE_MMI $([Microsoft.Management.Infrastructure.CimClass].Assembly.Location)"
}
finally { $class.Dispose() }
