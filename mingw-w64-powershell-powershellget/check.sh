#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
out=${1:?usage: check.sh NEW_OUTPUT [NEW_FEED]}
mkdir "$out";out=$(cd "$out" && pwd)
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false POWERSHELL_TELEMETRY_OPTOUT=1
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
cat > "$out/Restore.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="PowerShellGet" Version="[2.2.5]"/><PackageReference Include="PackageManagement" Version="[1.4.8.1]"/></ItemGroup></Project>
PROJECT
cat > "$out/NuGet.config" <<CONFIG
<configuration><packageSources><clear/><add key="installed-source" value="$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/library-packs)"/>
CONFIG
if [[ $# -ge 2 ]];then printf '<add key="new-source" value="%s"/>\n' "$(cygpath -am "$2")" >> "$out/NuGet.config";fi
printf '</packageSources>\n' >> "$out/NuGet.config"
if [[ $# -ge 2 ]];then
  printf '<packageSourceMapping><packageSource key="new-source"><package pattern="PowerShellGet"/></packageSource><packageSource key="installed-source"><package pattern="*"/></packageSource></packageSourceMapping>\n' >> "$out/NuGet.config"
fi
printf '</configuration>\n' >> "$out/NuGet.config"
${MINGW_PREFIX}/lib/dotnet/dotnet.exe restore "$(cygpath -am "$out/Restore.csproj")" --configfile "$(cygpath -am "$out/NuGet.config")" -v:minimal
module="$out/empty-packages/powershellget/2.2.5"
dependency="$out/empty-packages/packagemanagement/1.4.8.1/PackageManagement.psd1"
/usr/bin/python3 "$here/verify-restored.py" "$out" "$module"
/usr/bin/python3 "$here/make-fixtures.py" "$out/owned"
export APPDATA=$(cygpath -am "$out/owned/AppData") LOCALAPPDATA=$(cygpath -am "$out/owned/LocalAppData")
export ProgramFiles=$(cygpath -am "$out/owned/ProgramFiles") ProgramData=$(cygpath -am "$out/owned/ProgramData")
export PSModulePath="$(cygpath -am "$out/empty-packages");$(cygpath -am "$out/owned/ProgramFiles/PowerShell/Modules");$(cygpath -m "$MINGW_PREFIX")/lib/dotnet/tools/powershell-module-test-host/Modules"
for script in Smoke Offline;do
  timeout 600 ${MINGW_PREFIX}/bin/powershell-module-test-host "$(cygpath -am "$here/$script.ps1")" "$(cygpath -am "$module/PowerShellGet.psd1")" "$(cygpath -am "$dependency")" "$(cygpath -am "$out/owned")"
done
echo 'PASS complete source PowerShellGet fresh consumer and owned offline lifecycle checks'
