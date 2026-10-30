#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
out=${1:?usage: check.sh NEW_OUTPUT PINNED_SOURCE [NEW_FEED]}
source=$(cd "${2:?missing pinned source}" && pwd)
mkdir "$out";out=$(cd "$out" && pwd)
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false POWERSHELL_TELEMETRY_OPTOUT=1
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
cat > "$out/Restore.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="PSReadLine" Version="[2.3.6]"/></ItemGroup></Project>
PROJECT
cat > "$out/NuGet.config" <<CONFIG
<configuration><packageSources><clear/><add key="installed-source" value="$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/library-packs)"/>
CONFIG
if [[ $# -ge 3 ]];then printf '<add key="new-source" value="%s"/>\n' "$(cygpath -am "$3")" >> "$out/NuGet.config";fi
printf '</packageSources>\n' >> "$out/NuGet.config"
if [[ $# -ge 3 ]];then
    printf '<packageSourceMapping><packageSource key="new-source"><package pattern="PSReadLine"/></packageSource><packageSource key="installed-source"><package pattern="*"/></packageSource></packageSourceMapping>\n' >> "$out/NuGet.config"
fi
printf '</configuration>\n' >> "$out/NuGet.config"
${MINGW_PREFIX}/lib/dotnet/dotnet.exe restore "$(cygpath -am "$out/Restore.csproj")" --configfile "$(cygpath -am "$out/NuGet.config")" -v:minimal
module="$out/empty-packages/psreadline/2.3.6"
bash "$here/inspect.sh" "$module" "$out/metadata"
/usr/bin/python3 "$here/verify-restored.py" "$out" "$module" "$source" "$out/metadata"
mkdir "$out/smoke-owned"
timeout 60 ${MINGW_PREFIX}/bin/powershell-module-test-host "$(cygpath -am "$here/Smoke.ps1")" \
    "$(cygpath -am "$module/PSReadLine.psd1")" "$(cygpath -am "$out/smoke-owned")" "$(cygpath -am "$out/expected-resources.json")"
bash "$here/check-editing.sh" "$source" "$module" "$out/editing"
echo 'PASS source-only PSReadLine NuGet restore, full source/API/resource/forwarder gates, editing and fresh-process owned history recall'
