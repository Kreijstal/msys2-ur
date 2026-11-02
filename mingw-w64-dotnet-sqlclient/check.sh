#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check.sh NEW_OUTPUT PINNED_SOURCE [NEW_FEED]}";out=$(cd "$1" && pwd)
source=$(cd "${2:?missing pinned source}" && pwd)
feed=${MINGW_PREFIX}/lib/dotnet/library-packs
if [[ $# -ge 3 ]];then feed=$(cd "$3" && pwd);fi
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false POWERSHELL_TELEMETRY_OPTOUT=1
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export PSModulePath=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/tools/powershell-module-test-host/Modules)
unset 'System.Data.SqlClient.UseManagedSNIOnWindows'
cat > "$out/NuGet.config" <<XML
<configuration><packageSources><clear/><add key="source-built-package" value="$(cygpath -am "$feed")"/></packageSources></configuration>
XML
/usr/bin/python3 "$here/prepare-tds.py" "$source" "$out/protocol" --package
for project in values assets;do
 mkdir "$out/$project"
 if [[ $project == values ]];then file=Probe.cs;else file=CheckAssets.cs;fi
 cp "$here/$file" "$out/$project/"
 cat > "$out/$project/Check.csproj" <<XML
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0-windows</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Compile Include="$file"/><PackageReference Include="System.Data.SqlClient" Version="[4.9.1]"/></ItemGroup></Project>
XML
done
for project in protocol values assets;do
 if [[ $project == protocol ]];then file=Probe.csproj;else file=Check.csproj;fi
 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/$project/$file")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
done
/usr/bin/python3 "$here/verify-consumer.py" "$out" "$feed"
cd "$out/protocol"
timeout 150 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/protocol/bin/Release/net8.0-windows/Probe.dll")"
cd "$out"
timeout 40 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/values/bin/Release/net8.0-windows/Check.dll")" --no-network
timeout 40 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/assets/bin/Release/net8.0-windows/Check.dll")" "$(cygpath -am "$out/expected-assets.json")"
mkdir "$out/api"
cp "$here/CheckApi.cs" "$out/api/Program.cs"
cat > "$out/api/Check.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup></Project>
XML
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/api/Check.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
runtime="$out/protocol/bin/Release/net8.0-windows/runtimes/win/lib/net8.0"
${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/api/bin/Release/net8.0/Check.dll")" "$(cygpath -am "$out/cache/system.data.sqlclient/4.9.1/lib/net8.0/System.Data.SqlClient.dll")" "$(cygpath -am "$runtime")" "$(cygpath -am "$runtime")"
timeout 90 ${MINGW_PREFIX}/bin/powershell-module-test-host "$(cygpath -am "$here/PowerShell.ps1")" "$(cygpath -am "$runtime/System.Data.SqlClient.dll")" "$(cygpath -am "$out/protocol/bin/Release/net8.0-windows")" "$(cygpath -am "$out/expected-assets.json")" "$(cygpath -am "$out/powershell-owned")"
/usr/bin/python3 "$here/verify-consumer.py" "$out" "$feed"
echo 'PASS experimental installed-source SqlClient package: exact assets/resources/API,18 transport/TLS/SSPI scenarios, basic MARS/inclusive flow control and actual source PowerShell; full native/database parity remains open'
