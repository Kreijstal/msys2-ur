#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
module=$(cd "${1:?usage: inspect.sh MODULE_ROOT NEW_OUTPUT}" && pwd)
mkdir "${2:?missing new output}";out=$(cd "$2" && pwd)
runtime=/clang64/lib/dotnet/tools/powershell-module-test-host
cp "$here/InspectApi.cs" "$here/InspectIdentity.cs" "$out/"
for name in Api Identity;do
    mkdir "$out/$name"
    cat > "$out/$name/Inspect.csproj" <<PROJECT
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Compile Include="../Inspect$name.cs"/><Reference Include="Microsoft.CodeAnalysis"><HintPath>$(cygpath -am "$runtime/Microsoft.CodeAnalysis.dll")</HintPath></Reference><Reference Include="Microsoft.CodeAnalysis.CSharp"><HintPath>$(cygpath -am "$runtime/Microsoft.CodeAnalysis.CSharp.dll")</HintPath></Reference></ItemGroup></Project>
PROJECT
done
printf '<configuration><packageSources><clear/></packageSources></configuration>\n' > "$out/NuGet.config"
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
for name in Api Identity;do
    /clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/$name/Inspect.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
done
for pair in 'main|Microsoft.PowerShell.PSReadLine2.dll' 'pager|Microsoft.PowerShell.Pager.dll' 'forwarders|net6plus/Microsoft.PowerShell.PSReadLine.Polyfiller.dll';do
    name=${pair%%|*};file=${pair#*|}
    /clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$out/Identity/bin/Release/net8.0/Inspect.dll")" "$(cygpath -am "$module/$file")" > "$out/identity-$name.json"
done
# The published main module targets Desktop. Complete source runtime facades
# resolve mscorlib without discarding any API differences.
/clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$out/Api/bin/Release/net8.0/Inspect.dll")" \
    "$(cygpath -am /clang64/lib/dotnet/shared/Microsoft.NETCore.App/8.0.0)" \
    "$(cygpath -am "$module/Microsoft.PowerShell.PSReadLine2.dll")" "$(cygpath -am "$runtime")" > "$out/api.json"
