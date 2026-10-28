param([string]$Manifest,[string]$CheckDll,[string]$OwnedDirectory,[string]$Mode='primary')
$ErrorActionPreference='Stop'
Import-Module $Manifest -Force -ErrorAction Stop
Set-PSReadLineOption -HistorySaveStyle SaveNothing -HistorySavePath (Join-Path $OwnedDirectory editing-history.txt)
Add-Type -Path $CheckDll
if ($Mode -eq 'primary') {
    [Test.OwnedEditing]::Run((Join-Path $OwnedDirectory editing-history.txt))
} elseif ($Mode -eq 'reopen') {
    if (-not (Test-Path -LiteralPath (Join-Path $OwnedDirectory editing-history.txt))) { throw 'owned history file missing' }
    [Test.OwnedEditing]::Reopen()
} else { throw "unknown editing check mode $Mode" }
