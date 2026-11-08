param([Parameter(Mandatory=$true)][string]$Namespace)
$ErrorActionPreference='Stop'
$script:checks=0
function Require([bool]$Value,[string]$Message){$script:checks++;if(!$Value){throw $Message}}
$assembly=[Microsoft.Management.Infrastructure.CimSession].Assembly
Require ([IO.Path]::GetFullPath($assembly.Location).StartsWith([IO.Path]::GetFullPath($PSHOME)+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) 'Original console loads its bundled MMI'
$archive=[IO.Compression.ZipFile]::OpenRead((Join-Path $env:DOTNET_ROOT 'library-packs/microsoft.management.infrastructure.3.0.0.nupkg'))
try {
    $entry=$archive.GetEntry('lib/net8.0/Microsoft.Management.Infrastructure.dll')
    $stream=$entry.Open();$copy=[IO.MemoryStream]::new()
    try {$stream.CopyTo($copy);$expected=[Security.Cryptography.SHA256]::HashData($copy.ToArray())}finally{$stream.Dispose();$copy.Dispose()}
    Require ([Convert]::ToHexString($expected) -ceq [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($assembly.Location)))) 'Bundled MMI bytes match installed source package'
}finally{$archive.Dispose()}
foreach($dcom in @($false,$true)){
    $session=$null
    try {
        $arguments=@{Namespace=$Namespace;ClassName='MSYS2_MmiPortProbe';MethodName='Pump';Arguments=@{Mode=[uint32]9};ErrorAction='SilentlyContinue';ErrorVariable='providerErrors';WarningAction='SilentlyContinue';WarningVariable='providerWarnings'}
        if($dcom){$session=New-CimSession -SessionOption (New-CimSessionOption -Protocol Dcom);$arguments.CimSession=$session}
        $items=@(Invoke-CimMethod @arguments)
        Require ($providerErrors.Count -eq 1) 'One provider-origin error record'
        Require ($providerErrors[0].Exception.Message.Contains('provider-error-雪')) 'Provider error Unicode payload'
        Require ($providerWarnings.Count -eq 1) 'One provider-origin warning record'
        Require ($providerWarnings[0].Message -ceq 'provider-message-雪-π') 'Provider warning Unicode payload'
        $streams=@($items|Where-Object {$_.PSObject.TypeNames -contains 'Microsoft.Management.Infrastructure.CimMethodStreamedResult'})
        $finals=@($items|Where-Object {$_.PSObject.TypeNames -contains 'Microsoft.Management.Infrastructure.CimMethodResult'})
        Require ($items.Count -eq 6 -and $streams.Count -eq 5 -and $finals.Count -eq 1) 'Original cmdlet emits five stream items and one final result'
        Require ([string]::Join('|',@($streams|Where-Object ParameterName -eq Text|ForEach-Object ItemValue)) -ceq 'chunk-one-雪|chunk-two-π') 'Original cmdlet Unicode string chunks'
        Require ([string]::Join('|',@($streams|Where-Object ParameterName -eq Numbers|ForEach-Object ItemValue)) -ceq '7|42|123456') 'Original cmdlet numeric chunks'
        Require ($finals[0].ReturnValue -eq 0) 'Provider final return value'
        Require (!$finals[0].PromptAccepted) 'Fixture mode skips interactive prompts'
        Require ($finals[0].ErrorAccepted) 'Original cmdlet acknowledges nonterminating provider error'
        [GC]::Collect(2,[GCCollectionMode]::Forced,$true,$true);[GC]::WaitForPendingFinalizers()
        Require ($streams[0].ItemValue -ceq 'chunk-one-雪') 'Original cmdlet copied streamed value survives GC'
    }finally{if($null -ne $session){Remove-CimSession -CimSession $session}}
}
"PASS $script:checks original Invoke-CimMethod provider warning/error/stream/result/GC checks"
