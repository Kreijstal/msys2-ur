param([string]$Manifest,[string]$OwnedDirectory,[string]$ExpectedResources)
$ErrorActionPreference='Stop'
Import-Module $Manifest -Force -ErrorAction Stop
$module=Get-Module PSReadLine
if ($module.Version.ToString() -ne '2.3.6' -or $module.Guid.ToString() -ne '5714753b-2afd-4492-a5fd-01d9e2cff8b5') { throw 'PSReadLine module identity mismatch' }
$expected='Get-PSReadLineKeyHandler,Get-PSReadLineOption,Remove-PSReadLineKeyHandler,Set-PSReadLineKeyHandler,Set-PSReadLineOption'
if ((($module.ExportedCmdlets.Keys | Sort-Object) -join ',') -ne $expected) { throw 'PSReadLine cmdlet surface mismatch' }
$history=Join-Path $OwnedDirectory owned-history.txt
Set-PSReadLineOption -HistorySaveStyle SaveNothing -HistorySavePath $history -EditMode Emacs -BellStyle None
$options=Get-PSReadLineOption
if ($options.EditMode -ne 'Emacs' -or $options.HistorySaveStyle -ne 'SaveNothing' -or $options.HistorySavePath -ne $history) { throw 'PSReadLine options mismatch' }
Set-PSReadLineKeyHandler -Chord Ctrl+g -Function BackwardDeleteChar
$handler=Get-PSReadLineKeyHandler -Chord Ctrl+g
if ($handler.Function -ne 'BackwardDeleteChar') { throw 'PSReadLine key binding mismatch' }
Remove-PSReadLineKeyHandler -Chord Ctrl+g
if (Get-PSReadLineKeyHandler -Chord Ctrl+g) { throw 'PSReadLine key binding removal failed' }
$assembly=[Microsoft.PowerShell.PSConsoleReadLine].Assembly
if ($assembly.Location -ne (Join-Path (Split-Path $Manifest) Microsoft.PowerShell.PSReadLine2.dll)) { throw 'foreign PSReadLine implementation' }
if ($assembly.GetName().Version.ToString() -ne '2.3.6.0') { throw 'PSReadLine assembly identity mismatch' }
$manager=[Resources.ResourceManager]::new('Microsoft.PowerShell.PSReadLine.PSReadLineResources',$assembly)
try {
    $expected=Get-Content -Raw -LiteralPath $ExpectedResources | ConvertFrom-Json -AsHashtable
    $resources=$manager.GetResourceSet([Globalization.CultureInfo]::InvariantCulture,$true,$true)
    $actual=@{}
    foreach ($entry in $resources.GetEnumerator()) { $actual[$entry.Key]=$entry.Value }
    if ($expected.Count -ne 245 -or $actual.Count -ne $expected.Count) { throw 'PSReadLine resource inventory mismatch' }
    foreach ($name in $expected.Keys) {
        if ($resources.GetString($name) -cne $expected[$name]) { throw "PSReadLine resource mismatch: $name" }
    }
} finally { $manager.ReleaseAllResources() }
$forwarders=[Reflection.Assembly]::Load('Microsoft.PowerShell.PSReadLine.Polyfiller, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null')
$forwarderPath=Join-Path (Split-Path $Manifest) 'net6plus/Microsoft.PowerShell.PSReadLine.Polyfiller.dll'
if ([IO.Path]::GetFullPath($forwarders.Location) -ne [IO.Path]::GetFullPath($forwarderPath)) { throw 'foreign Core type forwarder implementation' }
$types=@($forwarders.GetForwardedTypes())
$typeNames=($types.FullName | Sort-Object) -join ','
if ($typeNames -ne 'System.Management.Automation.Subsystem.Prediction.CommandPrediction,System.Management.Automation.Subsystem.Prediction.PredictionClient,System.Management.Automation.Subsystem.Prediction.PredictionClientKind,System.Management.Automation.Subsystem.Prediction.PredictionResult,System.Management.Automation.Subsystem.Prediction.PredictiveSuggestion') { throw 'Core type forwarder surface mismatch' }
foreach ($type in $types) {
    if ($type.Assembly -ne [PowerShell].Assembly) { throw 'Core type forwarder did not resolve to source SMA' }
}
$pagerType=$assembly.GetType('Microsoft.PowerShell.PSConsoleReadLine').GetField('_pager',[Reflection.BindingFlags]'NonPublic,Instance').FieldType
if ([IO.Path]::GetFullPath($pagerType.Assembly.Location) -ne [IO.Path]::GetFullPath((Join-Path (Split-Path $Manifest) Microsoft.PowerShell.Pager.dll))) { throw 'foreign Pager implementation' }
if (Test-Path -LiteralPath $history) { throw 'disabled history persistence wrote a file' }
'PASS source PSReadLine import/exports/options/key handlers,245 resource strings, five Core forwarders and bundled source Pager'
