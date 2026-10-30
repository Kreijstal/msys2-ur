#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check.sh NEW_OUTPUT [NEW_FEED]}";out=$(cd "$1" && pwd)
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
cat > "$out/NuGet.config" <<XML
<configuration><packageSources><clear/><add key="installed-source" value="$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/library-packs)"/>
XML
if [[ $# -ge 2 ]];then printf '<add key="new-source" value="%s"/>\n' "$(cygpath -am "$2")" >> "$out/NuGet.config";fi
printf '</packageSources>\n' >> "$out/NuGet.config"
if [[ $# -ge 2 ]];then printf '<packageSourceMapping><packageSource key="new-source"><package pattern="Azure.Identity"/></packageSource><packageSource key="installed-source"><package pattern="*"/></packageSource></packageSourceMapping>\n' >> "$out/NuGet.config";fi
printf '</configuration>\n' >> "$out/NuGet.config"
cp "$here/Check.cs" "$here/OwnedEndpoint.cs" "$out/"
cat > "$out/Check.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><JsonSerializerIsReflectionEnabledByDefault>false</JsonSerializerIsReflectionEnabledByDefault><UseAppHost>false</UseAppHost><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Compile Include="Check.cs"/><Compile Include="OwnedEndpoint.cs"/><PackageReference Include="Azure.Identity" Version="[1.11.4]"/></ItemGroup></Project>
XML
${MINGW_PREFIX}/lib/dotnet/dotnet.exe restore "$(cygpath -am "$out/Check.csproj")" --configfile "$(cygpath -am "$out/NuGet.config")"
/usr/bin/python3 "$here/check-payload.py" stage "$out"
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/Check.csproj")" -c Release --no-restore -p:UseSharedCompilation=false -p:CscToolPath="$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/compiler-packs/roslyn-4.9.2)" -p:CscToolExe=csc49.cmd -v:minimal
timeout 100 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/bin/Release/net8.0/Check.dll")" "$(cygpath -am "$out/source-runtime-sha256.json")"
/usr/bin/python3 "$here/check-payload.py" verify "$out"
for tool in Api Pe;do
 mkdir "$out/$tool"
 if [[ $tool == Api ]];then source=InspectApi.cs;else source=InspectAssemblyMetadata.cs;fi
 cp "$here/$source" "$out/$tool/"
 cat > "$out/$tool/Inspect.csproj" <<XML
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Compile Include="$source"/>
XML
 if [[ $tool == Api ]];then printf '<PackageReference Include="Microsoft.CodeAnalysis.CSharp" Version="[4.9.2]"/>\n' >> "$out/$tool/Inspect.csproj";fi
 printf '</ItemGroup></Project>\n' >> "$out/$tool/Inspect.csproj"
 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/$tool/Inspect.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -p:CscToolPath="$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/compiler-packs/roslyn-4.9.2)" -p:CscToolExe=csc49.cmd -v:minimal
done
${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/Api/bin/Release/net8.0/Inspect.dll")" "$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0)" "$(cygpath -am "$out/bin/Release/net8.0/Azure.Identity.dll")" > "$out/api.json"
${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/Pe/bin/Release/net8.0/Inspect.dll")" "$(cygpath -am "$out/bin/Release/net8.0/Azure.Identity.dll")" > "$out/metadata.json"
/usr/bin/python3 "$here/compare.py" "$here" "$out"
echo 'PASS fresh source Azure.Identity consumer, real TLS/OIDC/auth-code/CAE behavior, exact API/identity/payload gates'
