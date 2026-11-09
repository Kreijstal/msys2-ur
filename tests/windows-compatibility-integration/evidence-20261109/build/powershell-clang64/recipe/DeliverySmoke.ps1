param([string] $SourceArchive = (Join-Path $env:DOTNET_ROOT 'library-packs/microsoft.management.infrastructure.3.0.0.nupkg'))
$ErrorActionPreference = 'Stop'
$script:checks = 0
$hidden = [Reflection.BindingFlags]'Instance,NonPublic'
function Require([bool] $Value, [string] $Message) {
    $script:checks++
    if (!$Value) { throw $Message }
}
function Handle([Microsoft.Management.Infrastructure.Options.CimSubscriptionDeliveryOptions] $Options) {
    return $Options.GetType().GetProperty('SubscriptionDeliveryOptionsHandle', $hidden).GetValue($Options)
}
function Invoke-Native([object] $Native, [string] $Name, [object[]] $Arguments) {
    $result = $Native.GetType().GetMethod($Name, $hidden).Invoke($Native, $Arguments)
    Require ([uint32]$result -eq 0) "Native $Name succeeded"
}
function Credential-Count([object] $Native) {
    [object[]] $arguments = @([uint32]0)
    Invoke-Native $Native 'GetCredentialsCount' $arguments
    return [uint32]$arguments[0]
}
function Credential-Record([object] $Native, [string] $Name) {
    $count = Credential-Count $Native
    for ([uint32]$index = 0; $index -lt $count; $index++) {
        [object[]] $arguments = @($index, $null, $null, $null)
        Invoke-Native $Native 'GetCredentialsAt' $arguments
        if ($arguments[1] -ceq $Name) {
            return [pscustomobject]@{ Index=$index; Value=$arguments[2]; Flags=[uint32]$arguments[3] }
        }
    }
    throw "Native credential option not found: $Name"
}
function Field([object] $Value, [string] $Name) {
    return $Value.GetType().GetField($Name, $hidden).GetValue($Value)
}
function Read-Interval([object] $Native, [string] $Name) {
    $valueType = $assembly.GetType('Microsoft.Management.Infrastructure.Native.MI_Value', $true)
    $value = [Activator]::CreateInstance($valueType, $true)
    try {
        [object[]] $arguments = @($Name, $value, $null, $null, $null)
        Invoke-Native $Native 'GetOption' $arguments
        $datetime = $valueType.GetProperty('Datetime', $hidden).GetValue($value)
        return $datetime.GetType().GetMethod('ConvertFromNativeLayer', $hidden).Invoke($datetime, [object[]]@())
    }
    finally { $value.Dispose() }
}

$assembly = [Microsoft.Management.Infrastructure.CimSession].Assembly
$dll = [IO.Path]::GetFullPath($assembly.Location)
Require ($dll.StartsWith([IO.Path]::GetFullPath($PSHOME) + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) 'PowerShell loads its bundled MMI'
$archive = [IO.Compression.ZipFile]::OpenRead($SourceArchive)
try {
    $entry = $archive.GetEntry('lib/net8.0/Microsoft.Management.Infrastructure.dll')
    Require ($null -ne $entry) 'Source archive implementation asset'
    $stream = $entry.Open(); $copy = [IO.MemoryStream]::new()
    try { $stream.CopyTo($copy); $expected = [Security.Cryptography.SHA256]::HashData($copy.ToArray()) }
    finally { $stream.Dispose(); $copy.Dispose() }
    $actual = [Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($dll))
    Require ([Convert]::ToHexString($actual) -ceq [Convert]::ToHexString($expected)) 'Bundled MMI matches installed source package bytes'
}
finally { $archive.Dispose() }

$options = [Microsoft.Management.Infrastructure.Options.CimSubscriptionDeliveryOptions]::new()
$clone = $null
$password = [Security.SecureString]::new()
try {
    $native = Handle $options
    Require ((Credential-Count $native) -eq 0) 'Public constructor creates empty native options'
    foreach ($character in 'fixture-π-密碼'.ToCharArray()) { $password.AppendChar($character) }
    $credential = [Microsoft.Management.Infrastructure.Options.CimCredential]::new([Microsoft.Management.Infrastructure.Options.PasswordAuthenticationMechanism]::Negotiate, 'fixture-domain-é', 'fixture-user-名', $password)
    $password.Clear(); $password.Dispose()
    $options.AddCredentials('password', $credential, 0)
    $options.AddCredentials('implicit', [Microsoft.Management.Infrastructure.Options.CimCredential]::new([Microsoft.Management.Infrastructure.Options.ImpersonatedAuthenticationMechanism]::Negotiate), 0)
    Require ((Credential-Count $native) -eq 2) 'Public AddCredentials populates native storage'
    $record = Credential-Record $native 'password'
    $mechanism = $record.Value.GetType().GetProperty('authenticationTypeString', $hidden).GetValue($record.Value)
    Require ($mechanism -ceq 'NegoWithCreds' -and $record.Flags -eq 0) 'Native password mechanism/flags'
    $pair = Field (Field $record.Value 'credentials') 'usernamePassword'
    Require ([Runtime.InteropServices.Marshal]::PtrToStringUni((Field $pair 'domain')) -ceq 'fixture-domain-é') 'Native Unicode credential domain'
    Require ([Runtime.InteropServices.Marshal]::PtrToStringUni((Field $pair 'username')) -ceq 'fixture-user-名') 'Native Unicode credential user'
    $options.SetInterval('interval', [TimeSpan]::FromTicks(171234560), 0)
    Require ((Read-Interval $native 'interval') -eq [TimeSpan]::FromTicks(171234560)) 'Public SetInterval preserves native duration'
    $clone = [Microsoft.Management.Infrastructure.Options.CimSubscriptionDeliveryOptions]::new($options)
    $options.Dispose(); $options.Dispose()
    [GC]::Collect(2, [GCCollectionMode]::Forced, $true, $true); [GC]::WaitForPendingFinalizers()
    $cloned = Handle $clone
    Require ((Credential-Count $cloned) -eq 2) 'Clone credentials survive original disposal/GC'
    Require ((Read-Interval $cloned 'interval') -eq [TimeSpan]::FromTicks(171234560)) 'Clone interval survives original disposal'
    $record = Credential-Record $cloned 'password'
    [object[]] $sizing = @($record.Index, $null, [IntPtr]::Zero, [uint32]0, $null, $null)
    [void]$cloned.GetType().GetMethod('GetCredentialsPasswordAt', $hidden).Invoke($cloned, $sizing)
    [uint32]$length = $sizing[4]
    Require ($length -gt 0) 'Native password readback buffer size'
    $buffer = [Runtime.InteropServices.Marshal]::AllocHGlobal([int]($length * 2))
    try {
        [object[]] $read = @($record.Index, $null, $buffer, $length, $null, $null)
        Invoke-Native $cloned 'GetCredentialsPasswordAt' $read
        Require ([Runtime.InteropServices.Marshal]::PtrToStringUni($buffer) -ceq 'fixture-π-密碼') 'Native password survives caller SecureString and original options disposal'
    }
    finally {
        for ($index = 0; $index -lt ($length * 2); $index++) { [Runtime.InteropServices.Marshal]::WriteByte($buffer, $index, 0) }
        [Runtime.InteropServices.Marshal]::FreeHGlobal($buffer)
    }
    $clone.Dispose(); $clone.Dispose()
    $rejected = $false
    try { $clone.SetNumber('disposed', 1, 0) } catch [ObjectDisposedException] { $rejected = $true }
    Require ($rejected) 'Disposed delivery options reject updates'
}
finally { $password.Dispose(); $options.Dispose(); if ($null -ne $clone) { $clone.Dispose() } }
Write-Output "PASS $script:checks PowerShell native delivery credential/interval/clone/lifetime checks"
