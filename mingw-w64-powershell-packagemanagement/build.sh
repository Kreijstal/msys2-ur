#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
out=$(cd "${1:?usage: build.sh PREPARED_ROOT}" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false POWERSHELL_TELEMETRY_OPTOUT=1
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
printf '<configuration><packageSources><clear/><add key="source" value="%s"/></packageSources></configuration>\n' "$(cygpath -am /clang64/lib/dotnet/library-packs)" > "$out/NuGet.config"
cd "$out/oneget"
for name in Microsoft.PackageManagement Microsoft.PackageManagement.CoreProviders Microsoft.PackageManagement.MetaProvider.PowerShell Microsoft.PowerShell.PackageManagement Microsoft.PackageManagement.NuGetProvider;do
    timeout 90 /clang64/bin/powershell-module-test-host "$(cygpath -am "$out/oneget/src/New-StronglyTypedCsFileForResx.ps1")" "$name"
done
for name in Microsoft.PackageManagement Microsoft.PackageManagement.ArchiverProviders Microsoft.PackageManagement.CoreProviders Microsoft.PackageManagement.MetaProvider.PowerShell Microsoft.PowerShell.PackageManagement Microsoft.PackageManagement.NuGetProvider;do
    file="$name.csproj";[[ $name != Microsoft.PackageManagement.NuGetProvider ]]||file=NuGetProvider.csproj
    /clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/oneget/src/$name/$file")" -c Debug \
        --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
done
