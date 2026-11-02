param([Parameter(Mandatory)][string]$Fixtures,[Parameter(Mandatory)][string]$Feed,[Parameter(Mandatory)][string]$Output)
$ErrorActionPreference='Stop'
$env:PSModulePath=Join-Path $PSHOME 'Modules'
$signer=[System.Security.Cryptography.X509Certificates.X509Certificate2]::new((Join-Path $Fixtures 'signer.cer'))
$tsa=[System.Security.Cryptography.X509Certificates.X509Certificate2]::new((Join-Path $Fixtures 'tsa.cer'))
$checks=[System.Collections.Generic.List[object]]::new()
try {
    $cases=@(
        @{Name='fixture.exe';Status='NotSigned';Type='None'},
        @{Name='unsigned.ps1';Status='NotSigned';Type='None'},
        @{Name='signed.exe';Status='UnknownError';Type='Authenticode'},
        @{Name='signed.ps1';Status='UnknownError';Type='Authenticode'},
        @{Name='timestamped.exe';Status='UnknownError';Type='Authenticode';Timestamp=$true},
        @{Name='tampered.exe';Status='HashMismatch';Type='Authenticode'},
        @{Name='kernel32.dll';Status='Valid';Type='Catalog';Windows=$true}
    )
    foreach($case in $cases) {
        $path=if($case.Windows){Join-Path $env:WINDIR 'System32/kernel32.dll'}else{Join-Path $Fixtures $case.Name}
        $stream=[IO.File]::OpenRead($path)
        try {$nativeSignature=[Microsoft.Security.Extensions.FileSignatureInfo]::GetFromFileStream($stream)} finally {$stream.Dispose()}
        try {
            $expectedNative=if($case.Status -eq 'NotSigned'){'Unsigned'}elseif($case.Status -eq 'Valid'){'SignedAndTrusted'}elseif($case.Status -eq 'HashMismatch'){'Invalid'}else{'SignedAndNotTrusted'}
            if($nativeSignature.State.ToString() -ne $expectedNative){throw "$($case.Name) native source state: $($nativeSignature.State)"}
            if($case.Status -eq 'UnknownError' -and $nativeSignature.StateReason.ToString() -ne 'UntrustedRoot'){throw 'Self-signed native source reason differs'}
            $nativeState=$nativeSignature.State.ToString();$nativeReason=$nativeSignature.StateReason.ToString()
        } finally {if($nativeSignature.SigningCertificate){$nativeSignature.SigningCertificate.Dispose()};if($nativeSignature.TimestampCertificate){$nativeSignature.TimestampCertificate.Dispose()}}
        $signature=Get-AuthenticodeSignature -LiteralPath $path -ErrorAction Stop
        if($signature.Status.ToString() -ne $case.Status){throw "$($case.Name) status: $($signature.Status), expected $($case.Status): $($signature.StatusMessage)"}
        if($signature.SignatureType.ToString() -ne $case.Type){throw "$($case.Name) signature type: $($signature.SignatureType)"}
        if($case.Status -eq 'NotSigned') {
            if($null -ne $signature.SignerCertificate){throw 'Unsigned fixture has a signer'}
        } elseif(!$case.Windows) {
            if($signature.SignerCertificate.Thumbprint -ne $signer.Thumbprint){throw "$($case.Name) signer identity"}
            if($signature.IsOSBinary){throw 'Owned fixture classified as an OS binary'}
        } elseif(!$signature.IsOSBinary -or !$signature.SignerCertificate){throw 'Windows catalog/OS identity'}
        if($case.Timestamp -and $signature.TimeStamperCertificate.Thumbprint -ne $tsa.Thumbprint){throw 'Offline timestamp certificate identity'}
        $checks.Add([ordered]@{File=$case.Name;NativeState=$nativeState;NativeReason=$nativeReason;Status=$signature.Status.ToString();SignatureType=$signature.SignatureType.ToString();IsOSBinary=$signature.IsOSBinary;SignerThumbprint=$signature.SignerCertificate.Thumbprint;TimestampThumbprint=$signature.TimeStamperCertificate.Thumbprint})
        Write-Output "PASS $($case.Name): $($signature.Status)/$($signature.SignatureType)"
    }
    $assembly=[Microsoft.Security.Extensions.FileSignatureInfo].Assembly
    $assemblyPath=[IO.Path]::GetFullPath($assembly.Location)
    if($assemblyPath -ne [IO.Path]::GetFullPath((Join-Path $PSHOME 'getfilesiginforedistwrapper.dll'))){throw "Foreign signature wrapper: $assemblyPath"}
    $native=@([Diagnostics.Process]::GetCurrentProcess().Modules | Where-Object {$_.ModuleName -eq 'msys-file-signature.dll'})
    if($native.Count -ne 1){throw 'Source native signature provider was not loaded exactly once'}
    $nativePath=[IO.Path]::GetFullPath($native[0].FileName)
    if(!$nativePath.StartsWith([IO.Path]::GetFullPath($PSHOME)+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw "Foreign source native provider: $nativePath"}
    $archivePath=Join-Path $Feed 'microsoft.security.extensions.1.4.0.nupkg'
    $archive=[IO.Compression.ZipFile]::OpenRead($archivePath)
    try {
        $payloads=@(
            @{Member='lib/net8.0/getfilesiginforedistwrapper.dll';Path=$assemblyPath},
            @{Member='runtimes/win-x64/native/msys-file-signature.dll';Path=$nativePath}
        )
        foreach($payload in $payloads){
            $stream=$archive.GetEntry($payload.Member).Open()
            try{$expected=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($stream))}finally{$stream.Dispose()}
            if((Get-FileHash -LiteralPath $payload.Path -Algorithm SHA256).Hash -ne $expected){throw "Installed source package bytes differ: $($payload.Path)"}
        }
    } finally {$archive.Dispose()}
    [ordered]@{PowerShellVersion=$PSVersionTable.PSVersion.ToString();Apartment=[Threading.Thread]::CurrentThread.GetApartmentState().ToString();Checks=$checks;SourceWrapper=$assemblyPath;SourceNativeProvider=$nativePath;InstalledSourceArchive=$archivePath;ExactSourceArchiveBytesVerified=$true;OriginalPowerShellNonValidSignatureWinVerifyTrustFallbackVerified=$true;CertificatesAddedToTrustStores=$false;RevocationExplicitDistrustExpiredEnterpriseMultipleSignaturesVerified=$false;FullDependencyGoalComplete=$false} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Output -Encoding utf8
    'PASS packaged Get-AuthenticodeSignature, seven trust/signature cases and exact source managed/native provider bytes'
} finally {$signer.Dispose();$tsa.Dispose()}
