#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
source=$(cd "${1:?usage: check-editing.sh PINNED_SOURCE MODULE_ROOT NEW_OUTPUT}" && pwd)
module=$(cd "${2:?missing module root}" && pwd)
mkdir "${3:?missing new output}";out=$(cd "$3" && pwd)
cp "$source/test/MockConsole.cs" "$out/MockConsole.cs"
cp "$here/EditingCheck.cs" "$out/EditingCheck.cs"
cat > "$out/Check.csproj" <<PROJECT
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><AssemblyName>PSReadLine.Tests</AssemblyName><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Compile Include="MockConsole.cs"/><Compile Include="EditingCheck.cs"/><Reference Include="Microsoft.PowerShell.PSReadLine2"><HintPath>$(cygpath -am "$module/Microsoft.PowerShell.PSReadLine2.dll")</HintPath><Private>false</Private></Reference><Reference Include="System.Management.Automation"><HintPath>$(cygpath -am /clang64/lib/dotnet/tools/powershell-module-test-host/System.Management.Automation.dll)</HintPath><Private>false</Private></Reference></ItemGroup></Project>
PROJECT
printf '<configuration><packageSources><clear/></packageSources></configuration>\n' > "$out/NuGet.config"
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/Check.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
for mode in primary reopen;do
    timeout 90 /clang64/bin/powershell-module-test-host "$(cygpath -am "$here/RunEditing.ps1")" \
        "$(cygpath -am "$module/PSReadLine.psd1")" "$(cygpath -am "$out/bin/Release/net8.0/PSReadLine.Tests.dll")" "$(cygpath -am "$out")" "$mode"
done
