#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check.sh NEW_OUTPUT [NEW_FEED] [INSTALLED_MODULE]}";out=$(cd "$1" && pwd)
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false POWERSHELL_TELEMETRY_OPTOUT=1
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export PSModulePath=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/tools/powershell-module-test-host/Modules)
new_source=false
installed_feed=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/library-packs)
if [[ $# -ge 2 ]];then
 proposed_feed=$(cygpath -am "$2")
 if [[ ${proposed_feed,,} != ${installed_feed,,} ]];then new_source=true;fi
fi
cat > "$out/NuGet.config" <<XML
<configuration><packageSources><clear/><add key="installed-source" value="$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/library-packs)"/>
XML
if $new_source;then printf '<add key="new-source" value="%s"/>\n' "$proposed_feed" >> "$out/NuGet.config";fi
printf '</packageSources>\n' >> "$out/NuGet.config"
if $new_source;then printf '<packageSourceMapping><packageSource key="new-source"><package pattern="Microsoft.PowerShell.PSResourceGet"/></packageSource><packageSource key="installed-source"><package pattern="*"/></packageSource></packageSourceMapping>\n' >> "$out/NuGet.config";fi
printf '</configuration>\n' >> "$out/NuGet.config"
cat > "$out/Restore.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.PowerShell.PSResourceGet" Version="[1.1.1]"/></ItemGroup></Project>
XML
${MINGW_PREFIX}/lib/dotnet/dotnet.exe restore "$(cygpath -am "$out/Restore.csproj")" --configfile "$(cygpath -am "$out/NuGet.config")" -v:minimal
module="$out/cache/microsoft.powershell.psresourceget/1.1.1"
modules=("$module")
mkdir "$out/relocated"
cp -R "$module" "$out/relocated/Microsoft.PowerShell.PSResourceGet"
modules+=("$out/relocated/Microsoft.PowerShell.PSResourceGet")
if [[ $# -ge 3 ]];then /usr/bin/python3 "$here/verify-restored.py" "$module" "$3";modules+=("$(cd "$3" && pwd)");fi
index=0
for path in "${modules[@]}";do
 /usr/bin/python3 "$here/verify-restored.py" "$path"
 timeout 100 ${MINGW_PREFIX}/bin/powershell-module-test-host "$(cygpath -am "$here/Smoke.ps1")" "$(cygpath -am "$path/Microsoft.PowerShell.PSResourceGet.psd1")" "$(cygpath -am "$out/smoke-$index")"
 timeout 180 ${MINGW_PREFIX}/bin/powershell-module-test-host "$(cygpath -am "$here/Lifecycle.ps1")" "$(cygpath -am "$path/Microsoft.PowerShell.PSResourceGet.psd1")" "$(cygpath -am "$out/lifecycle-$index")"
 index=$((index+1))
done
for tool in Api Pe;do
 mkdir "$out/$tool"
 if [[ $tool == Api ]];then source=InspectApi.cs;else source=InspectAssemblyMetadata.cs;fi
 cp "$here/$source" "$out/$tool/"
 cat > "$out/$tool/Inspect.csproj" <<XML
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Compile Include="$source"/>
XML
 if [[ $tool == Api ]];then printf '<PackageReference Include="Microsoft.CodeAnalysis.CSharp" Version="[4.9.2]"/>\n' >> "$out/$tool/Inspect.csproj";fi
 printf '</ItemGroup></Project>\n' >> "$out/$tool/Inspect.csproj"
 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/$tool/Inspect.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
done
mkdir "$out/engine-metadata"
cp ${MINGW_PREFIX}/lib/dotnet/tools/powershell-module-test-host/System.Management.Automation.dll "$out/engine-metadata/"
${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/Api/bin/Release/net8.0/Inspect.dll")" "$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0)" "$(cygpath -am "$module/Microsoft.PowerShell.PSResourceGet.dll")" "$(cygpath -am "$module/dependencies")" "$(cygpath -am "$out/engine-metadata")" > "$out/api.json"
${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/Pe/bin/Release/net8.0/Inspect.dll")" "$(cygpath -am "$module/Microsoft.PowerShell.PSResourceGet.dll")" > "$out/metadata.json"
/usr/bin/python3 "$here/compare.py" "$here" "$out"
echo 'PASS fresh/relocated source PSResourceGet: full module, script metadata, repository/package/dependency lifecycle, exact API/identity and payload/license gates'
