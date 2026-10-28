param([string]$PesterManifest, [string]$OwnedOutput)
$ErrorActionPreference = 'Stop'
Import-Module $PesterManifest -Force -ErrorAction Stop
$feature = "Feature: Owned source parser`n  Scenario: parse`n    Given an owned fixture`n"
$parser = [Gherkin.Parser]::new()
$document = $parser.Parse([System.IO.StringReader]::new($feature))
if ($document.Feature.Name -ne 'Owned source parser' -or $document.Feature.Children[0].Steps[0].Text -ne 'an owned fixture') { throw 'source Gherkin/Pester parser mismatch' }
$test = Join-Path $OwnedOutput 'Owned.Tests.ps1'
@'
Describe 'Owned source Pester smoke' {
    It 'executes the original assertion engine' { 42 | Should -Be 42 }
    It 'runs script compilation through original Add-Type' {
        $type = Add-Type -TypeDefinition 'public static class PesterOwnedCompile { public static int Value() => 84; }' -PassThru
        $type::Value() | Should -Be 84
    }
}
'@ | Set-Content -LiteralPath $test
$result = Invoke-Pester -Script $test -PassThru -Show Summary
if ($result.FailedCount -ne 0 -or $result.PassedCount -ne 2) { throw 'original source Pester smoke failed' }
'PASS original source Pester4 assertions, source Gherkin parser and original Add-Type'
