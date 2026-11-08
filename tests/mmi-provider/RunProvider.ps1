param([Parameter(Mandatory=$true)][string]$BuildRoot,[string]$Dotnet,[string]$ManagedAssembly,[string]$PowerShell)
$ErrorActionPreference='Stop'
if(!([Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'This disposable provider registration test requires an elevated shell'}
Add-Type -AssemblyName System.Management
$BuildRoot=[IO.Path]::GetFullPath($BuildRoot)
$identity=[Guid]::NewGuid().ToString('N')
$name='MSYS2_MmiPort_'+$identity
$namespace='root/'+$name
$provider='MSYS2_MmiProvider_'+$identity
$run=Join-Path $BuildRoot ('run-'+$identity)
$null=[IO.Directory]::CreateDirectory($run)
$dll=Join-Path $BuildRoot 'provider.dll'
$classes=[Microsoft.Win32.Registry]::ClassesRoot.OpenSubKey('CLSID')
$before=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach($key in $classes.GetSubKeyNames()){$null=$before.Add($key)}
$classes.Dispose()
$providerId=(Get-Content -Raw (Join-Path $BuildRoot 'provider-id.json')|ConvertFrom-Json).clsid
if($before.Contains($providerId)){throw 'Fixture CLSID already exists; refusing registration'}
$cimom=[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey('SOFTWARE\Microsoft\WBEM\CIMOM')
$autorecoverBefore=@($cimom.GetValue('Autorecover MOFs'));$cimom.Dispose()
$winrmBefore=(Get-Service WinRM).Status.ToString()
$state=[ordered]@{ namespace=$namespace;provider=$provider;provider_clsid=$providerId;registration_exit=$null;native_exit=$null;managed_exit=$null;powershell_exits=@();host_exit=$null;namespace_removed=$false;com_keys_removed=@();cleanup_errors=@();autorecover_unchanged=$false;winrm_unchanged=$false;complete=$false }
$state|ConvertTo-Json -Depth 6|Set-Content -Encoding UTF8 (Join-Path $run 'results.json')
$created=$false;$hostProcess=$null;$failure=$null
function Run-Client([string]$Exe,[string[]]$Arguments,[string]$Log,[int]$Timeout) {
    $process=Start-Process -FilePath $Exe -ArgumentList @($Arguments|ForEach-Object {'"'+$_+'"'}) -NoNewWindow -PassThru -RedirectStandardOutput ($Log+'.out') -RedirectStandardError ($Log+'.err')
    # Retain the native process handle before a fast child exits.
    $null=$process.Handle
    try {
        if(!$process.WaitForExit($Timeout)){$process.Kill();$process.WaitForExit();throw 'Client timeout'}
        $process.WaitForExit();return [int]$process.GetType().GetProperty('ExitCode').GetValue($process)
    }
    finally {$process.Dispose()}
}
try {
    $namespaceClass=[System.Management.ManagementClass]::new('root','__Namespace',$null)
    try {$instance=$namespaceClass.CreateInstance();try {$instance['Name']=$name;$options=[System.Management.PutOptions]::new();$options.Type=[System.Management.PutType]::CreateOnly;$null=$instance.Put($options);$created=$true} finally {$instance.Dispose()}} finally {$namespaceClass.Dispose()}
    Push-Location $run
    try {
        $output=& "$env:SystemRoot\System32\Register-CimProvider.exe" -Namespace $namespace -ProviderName $provider -Path $dll -Decoupled 'O:BAG:BAD:(A;;0x1;;;BA)' -Impersonation True -NoAutorecover -GenerateUnregistration -Verbose 2>&1
        $state.registration_exit=$LASTEXITCODE
        $output|Out-File -Encoding UTF8 (Join-Path $run 'registration.txt')
        if($state.registration_exit -ne 0){throw "Provider registration failed: $($state.registration_exit)"}
    } finally {Pop-Location}
    $stop=Join-Path $run 'stop'
    $hostProcess=Start-Process -FilePath (Join-Path $BuildRoot 'provider-host.exe') -ArgumentList @($namespace,$provider,('"'+$stop+'"')) -PassThru -NoNewWindow -RedirectStandardOutput (Join-Path $run 'provider.out') -RedirectStandardError (Join-Path $run 'provider.err')
    $null=$hostProcess.Handle
    $ready=$false
    for($attempt=0;$attempt -lt 100;$attempt++){
        if($hostProcess.HasExited){throw 'Provider host exited before ready'}
        if((Get-Content -Raw (Join-Path $run 'provider.out')) -match 'PROVIDER READY'){$ready=$true;break}
        Start-Sleep -Milliseconds 100
    }
    if(!$ready){throw 'Provider host readiness timeout'}
    $state.native_exit=Run-Client (Join-Path $BuildRoot 'native-client.exe') @($namespace) (Join-Path $run 'native') 45000
    if($Dotnet -and $ManagedAssembly){$state.managed_exit=Run-Client $Dotnet @($ManagedAssembly,$namespace) (Join-Path $run 'managed') 180000}
    if($PowerShell){
        foreach($mode in @('STA','MTA')){
            $state.powershell_exits+=@(Run-Client $PowerShell @('-NoLogo','-NoProfile','-NonInteractive',('-'+$mode),'-ExecutionPolicy','Bypass','-File',(Join-Path $PSScriptRoot 'PowerShellProvider.ps1'),'-Namespace',$namespace) (Join-Path $run ('powershell-'+$mode)) 90000)
        }
    }
    if($state.native_exit -ne 0){throw "Native provider client failed: $($state.native_exit)"}
    if($null -ne $state.managed_exit -and $state.managed_exit -ne 0){throw "Managed provider client failed: $($state.managed_exit)"}
    if(@($state.powershell_exits|Where-Object {$_ -ne 0}).Count){throw 'Original PowerShell provider fixture failed'}
    $state.complete=$true
}
catch {$failure=$_;$_|Out-String|Set-Content -Encoding UTF8 (Join-Path $run 'failure.txt')}
finally {
    if($null -ne $hostProcess){
        try {
            [IO.File]::WriteAllText((Join-Path $run 'stop'),'stop')
            if(!$hostProcess.WaitForExit(15000)){$hostProcess.Kill();$hostProcess.WaitForExit()}
            $hostProcess.WaitForExit();$state.host_exit=[int]$hostProcess.GetType().GetProperty('ExitCode').GetValue($hostProcess)
        } catch {$state.cleanup_errors+=@($_.ToString())}
        finally {$hostProcess.Dispose()}
    }
    # The namespace was created with CreateOnly and contains only this fixture.
    if($created){
        try {
            $instance=[System.Management.ManagementObject]::new('root',('__Namespace.Name="'+$name+'"'),$null)
            try {$instance.Delete();$state.namespace_removed=$true} finally {$instance.Dispose()}
        } catch {$state.cleanup_errors+=@($_.ToString())}
    }
    # Registration can create a COM CLSID. Remove only a newly created key whose
    # default value or DLL path identifies this unique fixture.
    $classes=$null
    try {
        $classes=[Microsoft.Win32.Registry]::ClassesRoot.OpenSubKey('CLSID',$true)
        foreach($keyName in $classes.GetSubKeyNames()){
            if($before.Contains($keyName)){continue}
            $key=$classes.OpenSubKey($keyName);$owned=$false
            try {
                $owned=($keyName -ieq $providerId) -or ($key.GetValue('') -ceq $provider)
                $inproc=$key.OpenSubKey('InprocServer32')
                if($null -ne $inproc){try {$owned=$owned -or ($inproc.GetValue('') -ieq $dll)} finally {$inproc.Dispose()}}
            } finally {$key.Dispose()}
            if($owned){$classes.DeleteSubKeyTree($keyName);$state.com_keys_removed+=@($keyName)}
        }
        $remaining=$classes.OpenSubKey($providerId)
        if($null -ne $remaining){$remaining.Dispose();$state.cleanup_errors+=@('Fixture COM CLSID remains after cleanup')}
    } catch {$state.cleanup_errors+=@($_.ToString())} finally {if($classes){$classes.Dispose()}}
    $cimom=[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey('SOFTWARE\Microsoft\WBEM\CIMOM')
    try {$autorecoverAfter=@($cimom.GetValue('Autorecover MOFs'))} finally {$cimom.Dispose()}
    $state.autorecover_unchanged=(@(Compare-Object $autorecoverBefore $autorecoverAfter).Count -eq 0)
    $state.winrm_unchanged=((Get-Service WinRM).Status.ToString() -ceq $winrmBefore)
    $state.complete=$state.complete -and $state.namespace_removed -and $state.autorecover_unchanged -and $state.winrm_unchanged -and $state.host_exit -eq 0 -and $state.cleanup_errors.Count -eq 0
    $state|ConvertTo-Json -Depth 6|Set-Content -Encoding UTF8 (Join-Path $run 'results.json')
    "RESULTS $run"
    $state|ConvertTo-Json -Compress -Depth 6
}
if($failure){throw $failure}
if(!$state.complete){throw 'Provider cleanup invariant failed'}
