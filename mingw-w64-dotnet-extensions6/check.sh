#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
out=${1:?usage: check.sh NEW_OUTPUT [NEW_FEED]}
mkdir "$out";out=$(cd "$out" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
cat > "$out/NuGet.config" <<XML
<configuration><packageSources><clear/><add key="installed-source" value="$(cygpath -am /clang64/lib/dotnet/library-packs)"/>
XML
if [[ $# -ge 2 ]];then printf '<add key="new-source" value="%s"/>\n' "$(cygpath -am "$2")" >> "$out/NuGet.config";fi
printf '</packageSources>\n' >> "$out/NuGet.config"
if [[ $# -ge 2 ]];then
  printf '<packageSourceMapping><packageSource key="new-source"><package pattern="Microsoft.Extensions.Primitives"/><package pattern="Microsoft.Extensions.FileProviders.Abstractions"/><package pattern="Microsoft.Extensions.FileSystemGlobbing"/></packageSource><packageSource key="installed-source"><package pattern="*"/></packageSource></packageSourceMapping>\n' >> "$out/NuGet.config"
fi
printf '</configuration>\n' >> "$out/NuGet.config"
cp "$here/Check.cs" "$out/"
cat > "$out/Check.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Compile Include="Check.cs"/><PackageReference Include="Microsoft.Extensions.Primitives" Version="[6.0.0]"/><PackageReference Include="Microsoft.Extensions.FileProviders.Abstractions" Version="[6.0.0]"/><PackageReference Include="Microsoft.Extensions.FileSystemGlobbing" Version="[6.0.0]"/></ItemGroup></Project>
XML
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/Check.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
mkdir "$out/owned"
/clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$out/bin/Release/net8.0/Check.dll")" "$(cygpath -am "$out/owned")" "$(cygpath -am "$here/published-metadata.json")"
mkdir "$out/metadata" "$out/api"
cp "$here/InspectApi.cs" "$out/metadata/"
cat > "$out/metadata/Inspect.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Compile Include="InspectApi.cs"/><PackageReference Include="Microsoft.CodeAnalysis.CSharp" Version="[4.9.2]"/></ItemGroup></Project>
XML
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/metadata/Inspect.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
for name in Microsoft.Extensions.Primitives Microsoft.Extensions.FileProviders.Abstractions Microsoft.Extensions.FileSystemGlobbing;do
  /clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$out/metadata/bin/Release/net8.0/Inspect.dll")" E:/msys64/clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0 "$(cygpath -am "$out/bin/Release/net8.0/$name.dll")" > "$out/api/$name.json"
done
/usr/bin/python3 "$here/compare-api.py" "$here/published-api.json" "$out/api"
echo 'PASS fresh Extensions6 source-only consumer, owned behavior/resource checks and complete API comparison'
