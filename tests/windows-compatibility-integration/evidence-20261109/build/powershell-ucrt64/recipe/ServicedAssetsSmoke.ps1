param([string]$ReceiptPath = (Join-Path $PSHOME '../../../share/doc/powershell/serviced-runtime-assets.json'))
$ErrorActionPreference = 'Stop'
$receipt = Get-Content -Raw $ReceiptPath | ConvertFrom-Json
if (@($receipt.assets.PSObject.Properties | Where-Object { $_.Value.is_primary }).Count -ne 9) { throw 'Nine primary serviced assets required' }
if ('System.Diagnostics.EventLog.Messages' -notin $receipt.assets.PSObject.Properties.Name) { throw 'Source event-message companion required' }
foreach ($property in $receipt.assets.PSObject.Properties) {
    $name = $property.Name
    $record = $property.Value
    $expected = [IO.Path]::GetFullPath((Join-Path $PSHOME $record.relative_path))
    if ($record.is_primary) {
        $assembly = [Reflection.Assembly]::Load($name)
        if ($assembly.Location -ne $expected) { throw "Unserviced framework selection: $name at $($assembly.Location)" }
    }
    $digest = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($expected))).ToLowerInvariant()
    if ($digest -ne $record.sha256) { throw "Serviced source bytes differ: $name" }
    if ([Diagnostics.FileVersionInfo]::GetVersionInfo($expected).FileVersion -ne $record.file_version) { throw "Serviced file version differs: $name" }
}
Write-Output 'PASS nine serviced source runtime assets override older desktop framework copies'
