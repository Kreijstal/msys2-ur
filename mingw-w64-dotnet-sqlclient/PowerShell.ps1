param([string]$Implementation,[string]$FixtureDirectory,[string]$ExpectedAssets,[string]$OwnedRoot)
$ErrorActionPreference='Stop'
try {
function Require([bool]$Value,[string]$Message){if(-not $Value){throw $Message}}
New-Item -ItemType Directory -Path $OwnedRoot | Out-Null
$previousLocation=Get-Location
$previousProcessDirectory=[Environment]::CurrentDirectory
$key=$null;$certificate=$null;$endpoint=$null;$connection=$null;$command=$null
try {
    Set-Location $OwnedRoot
    [Environment]::CurrentDirectory=[IO.Path]::GetFullPath($OwnedRoot)
    $expected=Get-Content $ExpectedAssets -Raw | ConvertFrom-Json
    $assembly=[Reflection.Assembly]::LoadFrom($Implementation)
    Require ($assembly.Location -eq [IO.Path]::GetFullPath($Implementation)) 'PowerShell loads the package Windows runtime asset'
    Require ((Get-FileHash $assembly.Location -Algorithm SHA256).Hash.ToLowerInvariant() -eq $expected.implementation_sha256) 'PowerShell executing exact source package bytes'
    foreach($name in @('Microsoft.SqlServer.TDS','Microsoft.SqlServer.TDS.EndPoint','Microsoft.SqlServer.TDS.Servers')){
        [Reflection.Assembly]::LoadFrom((Join-Path $FixtureDirectory "$name.dll")) | Out-Null
    }
    $key=[Security.Cryptography.RSA]::Create(2048)
    $request=[Security.Cryptography.X509Certificates.CertificateRequest]::new('CN=localhost',$key,[Security.Cryptography.HashAlgorithmName]::SHA256,[Security.Cryptography.RSASignaturePadding]::Pkcs1)
    $certificate=$request.CreateSelfSigned([DateTimeOffset]::UtcNow.AddMinutes(-1),[DateTimeOffset]::UtcNow.AddHours(1))
    [IO.File]::WriteAllBytes((Join-Path $OwnedRoot 'TdsServerCertificate.pfx'),$certificate.Export([Security.Cryptography.X509Certificates.X509ContentType]::Pfx,'PLACEHOLDER'))
    $arguments=[Microsoft.SqlServer.TDS.Servers.TDSServerArguments]::new()
    $arguments.Encryption=[Microsoft.SqlServer.TDS.PreLogin.TDSPreLoginTokenEncryptionType]::NotSupported
    $server=[Microsoft.SqlServer.TDS.Servers.GenericTDSServer]::new($arguments)
    $endpoint=[Microsoft.SqlServer.TDS.EndPoint.TDSServerEndPoint]::new($server)
    $endpoint.ServerEndPoint=[Net.IPEndPoint]::new([Net.IPAddress]::Loopback,0)
    $endpoint.Start()
    $connection=[System.Data.SqlClient.SqlConnection]::new("Server=tcp:127.0.0.1,$($endpoint.ServerEndPoint.Port);User ID=fixture;Password=fixture;Encrypt=false;Pooling=false;Connect Timeout=5")
    $connection.Open()
    $command=$connection.CreateCommand()
    $command.CommandText='SELECT TOP (1) [encrypt_option] FROM [sys].[dm_exec_connections] WHERE [session_id] = @@SPID'
    Require ($command.ExecuteScalar() -eq 'FALSE') 'PowerShell SqlClient scalar query against original TDS peer'
    $reader=$command.ExecuteReader()
    try {
        Require ($reader.Read() -and $reader.GetName(0) -eq 'encrypt_option' -and $reader.GetString(0) -eq 'FALSE') 'PowerShell reader schema and row'
        Require (-not $reader.Read()) 'PowerShell reader DONE'
    } finally {$reader.Dispose()}
    foreach($module in [Diagnostics.Process]::GetCurrentProcess().Modules){
        Require ($module.ModuleName -ine 'sni.dll' -and $module.FileName -notmatch '\\Microsoft.NET\\Framework') 'PowerShell process loads no proprietary SNI or Framework implementation'
    }
    Write-Output 'PASS actual source PowerShell with installed SqlClient Windows asset: exact package bytes, owned original TDS peer scalar/reader/schema/DONE, no proprietary SNI or Framework implementation'
} finally {
    if($command){$command.Dispose()}
    if($connection){$connection.Dispose()}
    if($endpoint){$endpoint.Stop()}
    if($arguments){$arguments.EncryptionCertificate.Dispose()}
    if($certificate){$certificate.Dispose()}
    if($key){$key.Dispose()}
    $pfx=Join-Path $OwnedRoot 'TdsServerCertificate.pfx'
    if(Test-Path $pfx){Remove-Item $pfx -Force}
    Set-Location $previousLocation
    [Environment]::CurrentDirectory=$previousProcessDirectory
}
} catch { [Console]::Error.WriteLine($_.InvocationInfo.PositionMessage);[Console]::Error.WriteLine($_.ScriptStackTrace);[Console]::Error.WriteLine($_.Exception.ToString());throw }
