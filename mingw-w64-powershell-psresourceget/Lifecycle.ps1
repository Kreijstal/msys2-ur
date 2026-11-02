param([string]$ModuleManifest,[string]$OwnedRoot)
$ErrorActionPreference='Stop'
try {
function Require([bool]$Condition,[string]$Message){if(-not $Condition){throw $Message}}
Import-Module $ModuleManifest -Force -ErrorAction Stop
$id=[guid]::NewGuid().ToString('N')
$repoName="OwnedPSRG$id"
$moduleName="OwnedModule$id"
$dependencyName="OwnedDependency$id"
$store=Join-Path ([Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData)) 'PSResourceGet/PSResourceRepository.xml'
$storeExisted=Test-Path $store
$beforeRepos=@()
if($storeExisted){
    [xml]$beforeXml=Get-Content $store -Raw
    $beforeRepos=@($beforeXml.configuration.ChildNodes | ForEach-Object {$_.OuterXml})
}
New-Item -ItemType Directory -Path $OwnedRoot -ErrorAction Stop | Out-Null
$repo=New-Item -ItemType Directory -Path (Join-Path $OwnedRoot 'repository')
$saved=New-Item -ItemType Directory -Path (Join-Path $OwnedRoot 'saved')
$nupkgs=New-Item -ItemType Directory -Path (Join-Path $OwnedRoot 'nupkgs')
$sources=New-Item -ItemType Directory -Path (Join-Path $OwnedRoot 'sources')
$edition=if($Host.Version -ge [version]'6.0'){'PowerShell'}else{'WindowsPowerShell'}
$installBase=Join-Path ([Environment]::GetFolderPath([Environment+SpecialFolder]::MyDocuments)) "$edition/Modules"
foreach($name in @($moduleName,$dependencyName)){Require (-not(Test-Path (Join-Path $installBase $name))) 'unique module install path starts absent'}
$previousModulePath=$env:PSModulePath
$env:PSModulePath=$installBase+[IO.Path]::PathSeparator+$env:PSModulePath
$registered=$false
try {
    $existing=@(Microsoft.PowerShell.PSResourceGet\Get-PSResourceRepository -ErrorAction Stop)
    Require (-not($existing.Name -contains $repoName)) 'unique repository starts absent'
    $registeredRepo=Microsoft.PowerShell.PSResourceGet\Register-PSResourceRepository -Name $repoName -Uri $repo.FullName -ApiVersion Local -Trusted -Priority 42 -PassThru
    $registered=$true
    Require ($registeredRepo.Name -eq $repoName -and $registeredRepo.Trusted -and $registeredRepo.Priority -eq 42) 'register repository metadata'
    $changed=Microsoft.PowerShell.PSResourceGet\Set-PSResourceRepository -Name $repoName -Priority 43 -Trusted:$false -PassThru
    Require ($changed.Priority -eq 43 -and -not $changed.Trusted) 'set repository metadata'
    Microsoft.PowerShell.PSResourceGet\Set-PSResourceRepository -Name $repoName -Trusted
    $read=Microsoft.PowerShell.PSResourceGet\Get-PSResourceRepository -Name $repoName
    Require ($read.Name -eq $repoName -and $read.Trusted) 'get repository metadata'
    function Make-Source([string]$Name,[string]$Version,[string]$Function,[string]$Body,[bool]$NeedsDependency){
        $dir=New-Item -ItemType Directory -Path (Join-Path $sources "$Name-$Version/$Name") -Force
        Set-Content (Join-Path $dir "$Name.psm1") $Body -Encoding utf8
        $metadata=@{Path=(Join-Path $dir "$Name.psd1");RootModule="$Name.psm1";ModuleVersion=$Version;Guid=[guid]::NewGuid();Author='owned';Description='owned source package λ';FunctionsToExport=@($Function);CmdletsToExport=@();VariablesToExport=@();AliasesToExport=@()}
        if($NeedsDependency){$metadata.RequiredModules=@(@{ModuleName=$dependencyName;RequiredVersion='1.0.0'})}
        New-ModuleManifest @metadata
        return $dir.FullName
    }
    $dependency=Make-Source $dependencyName '1.0.0' 'Get-OwnedDependency' "function Get-OwnedDependency { 'dependency λ' }; Export-ModuleMember -Function Get-OwnedDependency" $false
    Microsoft.PowerShell.PSResourceGet\Publish-PSResource -Path $dependency -Repository $repoName
    function Publish-Owned([string]$Path){
        $originalPath=$env:PSModulePath
        try {
            $env:PSModulePath=(Split-Path $dependency -Parent)+[IO.Path]::PathSeparator+$originalPath
            Microsoft.PowerShell.PSResourceGet\Publish-PSResource -Path $Path -Repository $repoName
        } finally {
            $env:PSModulePath=$originalPath
            Remove-Module $dependencyName -Force -ErrorAction SilentlyContinue
        }
    }
    $first=Make-Source $moduleName '1.0.0' 'Get-OwnedGreeting' "function Get-OwnedGreeting { 'owned1-' + (Get-OwnedDependency) }; Export-ModuleMember -Function Get-OwnedGreeting" $true
    Publish-Owned $first
    $found=Microsoft.PowerShell.PSResourceGet\Find-PSResource -Name $moduleName -Repository $repoName
    Require ($found.Name -eq $moduleName -and $found.Version.ToString() -eq '1.0.0') 'publish/find local package'
    Microsoft.PowerShell.PSResourceGet\Save-PSResource -Name $moduleName -Version '[1.0.0]' -Repository $repoName -Path $saved.FullName -TrustRepository
    Require (Test-Path (Join-Path $saved "$moduleName/1.0.0/$moduleName.psm1")) 'save main module'
    Require (Test-Path (Join-Path $saved "$dependencyName/1.0.0/$dependencyName.psm1")) 'save resolves required dependency'
    Microsoft.PowerShell.PSResourceGet\Save-PSResource -Name $moduleName -Repository $repoName -Path $nupkgs.FullName -TrustRepository -AsNupkg
    Require (Test-Path (Join-Path $nupkgs "$moduleName.1.0.0.nupkg")) 'save original NuGet archive'
    Microsoft.PowerShell.PSResourceGet\Install-PSResource -Name $moduleName -Version '[1.0.0]' -Repository $repoName -Scope CurrentUser -TrustRepository -AcceptLicense -Quiet
    $installed=Microsoft.PowerShell.PSResourceGet\Get-InstalledPSResource -Name $moduleName -Scope CurrentUser
    Require ($installed.Version.ToString() -eq '1.0.0' -and $installed.Repository -eq $repoName) 'install/get installed source metadata'
    Require (Test-Path (Join-Path $installBase "$dependencyName/1.0.0/$dependencyName.psd1")) 'install resolves dependency'
    $second=Make-Source $moduleName '1.1.0' 'Get-OwnedGreeting' "function Get-OwnedGreeting { 'owned2-' + (Get-OwnedDependency) }; Export-ModuleMember -Function Get-OwnedGreeting" $true
    Publish-Owned $second
    $latest=Microsoft.PowerShell.PSResourceGet\Find-PSResource -Name $moduleName -Repository $repoName
    Require ($latest.Version.ToString() -eq '1.1.0') 'latest numeric version selected'
    Microsoft.PowerShell.PSResourceGet\Update-PSResource -Name $moduleName -Repository $repoName -Scope CurrentUser -TrustRepository -AcceptLicense -Quiet
    $updated=@(Microsoft.PowerShell.PSResourceGet\Get-InstalledPSResource -Name $moduleName -Scope CurrentUser)
    Require (@($updated | Where-Object {$_.Version.ToString() -eq '1.1.0'}).Count -eq 1) 'update installs new version'
    Import-Module (Join-Path $installBase "$moduleName/1.1.0/$moduleName.psd1") -Force
    Require ((Get-Module $dependencyName).ModuleBase -eq (Join-Path $installBase "$dependencyName/1.0.0")) 'executed dependency comes from installed location'
    Require ((Get-OwnedGreeting) -eq 'owned2-dependency λ') 'installed original module/dependency execute'
    Remove-Module $moduleName -Force
    Remove-Module $dependencyName -Force
    Microsoft.PowerShell.PSResourceGet\Uninstall-PSResource -Name $moduleName -Version '*' -Scope CurrentUser -Confirm:$false
    Microsoft.PowerShell.PSResourceGet\Uninstall-PSResource -Name $dependencyName -Version '*' -Scope CurrentUser -Confirm:$false
    foreach($name in @($moduleName,$dependencyName)){Require (-not(Test-Path (Join-Path $installBase "$name/1.0.0"))) 'uninstalled owned package'}
    $notFound=$false
    try{Microsoft.PowerShell.PSResourceGet\Find-PSResource -Name "Missing$id" -Repository $repoName -ErrorAction Stop | Out-Null}catch{$notFound=$_.FullyQualifiedErrorId -like 'PackageNotFound*'}
    Require $notFound 'missing package returns original error'
    Write-Output 'PASS original local repository register/get/set, publish/find, dependency save/install, NuGet save, installed metadata/update/module execution, uninstall and missing-package behavior'
}
finally {
    $env:PSModulePath=$previousModulePath
    if($registered){Microsoft.PowerShell.PSResourceGet\Unregister-PSResourceRepository -Name $repoName -ErrorAction Stop}
    foreach($name in @($moduleName,$dependencyName)){
        Remove-Module $name -Force -ErrorAction SilentlyContinue
        $path=Join-Path $installBase $name
        if(Test-Path $path){Remove-Item $path -Recurse -Force}
    }
    if($storeExisted){
        [xml]$afterXml=Get-Content $store -Raw
        $afterRepos=@($afterXml.configuration.ChildNodes | ForEach-Object {$_.OuterXml})
        foreach($entry in $beforeRepos){Require ($afterRepos -contains $entry) 'pre-existing repository entry preserved'}
    }
    else {
        # Remove only this run's auto-created default store, if nobody added entries.
        [xml]$created=Get-Content $store -Raw
        $entries=@($created.configuration.ChildNodes)
        if($entries.Count -eq 1 -and $entries[0].LocalName -eq 'Repository' -and $entries[0].GetAttribute('Name') -eq 'PSGallery' -and $entries[0].GetAttribute('Url') -eq 'https://www.powershellgallery.com/api/v2'){
            Remove-Item $store -Force
        }
    }
    Write-Output 'PASS owned repository/module cleanup; existing repository entries preserved'
}

} catch { [Console]::Error.WriteLine($_.InvocationInfo.PositionMessage); [Console]::Error.WriteLine($_.ScriptStackTrace); [Console]::Error.WriteLine($_.Exception.ToString()); throw }
