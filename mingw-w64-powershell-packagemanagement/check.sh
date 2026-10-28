#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
out=${1:?usage: check.sh NEW_OUTPUT PINNED_SOURCE PINNED_PROVIDER_SOURCE [NEW_FEED]}
source=$(cd "${2:?missing pinned source}" && pwd)
provider=$(cd "${3:?missing pinned provider}" && pwd)
mkdir "$out";out=$(cd "$out" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false POWERSHELL_TELEMETRY_OPTOUT=1
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
cat > "$out/Restore.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="PackageManagement" Version="[1.4.8.1]"/></ItemGroup></Project>
PROJECT
cat > "$out/NuGet.config" <<CONFIG
<configuration><packageSources><clear/><add key="installed-source" value="$(cygpath -am /clang64/lib/dotnet/library-packs)"/>
CONFIG
if [[ $# -ge 4 ]];then printf '<add key="new-source" value="%s"/>\n' "$(cygpath -am "$4")" >> "$out/NuGet.config";fi
printf '</packageSources>\n' >> "$out/NuGet.config"
if [[ $# -ge 4 ]];then
    printf '<packageSourceMapping><packageSource key="new-source"><package pattern="PackageManagement"/></packageSource><packageSource key="installed-source"><package pattern="*"/></packageSource></packageSourceMapping>\n' >> "$out/NuGet.config"
fi
printf '</configuration>\n' >> "$out/NuGet.config"
/clang64/lib/dotnet/dotnet.exe restore "$(cygpath -am "$out/Restore.csproj")" --configfile "$(cygpath -am "$out/NuGet.config")" -v:minimal
module="$out/empty-packages/packagemanagement/1.4.8.1"
bash "$here/inspect.sh" "$module/coreclr/netstandard2.0" "$out/metadata"
/usr/bin/python3 "$here/verify-restored.py" "$out" "$module" "$source" "$provider" "$out/metadata"
mkdir -p "$out/smoke/appdata" "$out/smoke/localappdata" "$out/smoke/programfiles"
export AppData=$(cygpath -am "$out/smoke/appdata") LocalAppData=$(cygpath -am "$out/smoke/localappdata") ProgramFiles=$(cygpath -am "$out/smoke/programfiles")
export PSModulePath=$(cygpath -am /clang64/lib/dotnet/tools/powershell-module-test-host/Modules)
timeout 90 /clang64/bin/powershell-module-test-host "$(cygpath -am "$here/Smoke.ps1")" \
    "$(cygpath -am "$module/PackageManagement.psd1")" "$(cygpath -am "$module/source-build/expected-resources.json")"
/usr/bin/python3 "$here/prepare-fixtures.py" "$out/offline"
mkdir -p "$out/offline/appdata" "$out/offline/localappdata" "$out/offline/programfiles"
export AppData=$(cygpath -am "$out/offline/appdata") LocalAppData=$(cygpath -am "$out/offline/localappdata") ProgramFiles=$(cygpath -am "$out/offline/programfiles")
timeout 120 /clang64/bin/powershell-module-test-host "$(cygpath -am "$here/Offline.ps1")" \
    "$(cygpath -am "$module/PackageManagement.psd1")" "$(cygpath -am "$out/offline")"
echo 'PASS restored source PackageManagement identity/API/resources, Core module/provider load and owned offline package/source lifecycle'
