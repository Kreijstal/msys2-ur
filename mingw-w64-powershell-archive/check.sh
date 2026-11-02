#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
out=${1:?usage: check.sh NEW_OUTPUT PINNED_ARCHIVE_SOURCE [NEW_FEED]}
source=$(cd "${2:?missing pinned source}" && pwd)
mkdir "$out";out=$(cd "$out" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false POWERSHELL_TELEMETRY_OPTOUT=1
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
cat > "$out/Restore.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.PowerShell.Archive" Version="[1.2.6]"/></ItemGroup></Project>
PROJECT
cat > "$out/NuGet.config" <<CONFIG
<configuration><packageSources><clear/><add key="installed-source" value="$(cygpath -am /clang64/lib/dotnet/library-packs)"/>
CONFIG
if [[ $# -ge 3 ]];then printf '<add key="new-source" value="%s"/>\n' "$(cygpath -am "$3")" >> "$out/NuGet.config";fi
printf '</packageSources>\n' >> "$out/NuGet.config"
if [[ $# -ge 3 ]];then
  printf '<packageSourceMapping><packageSource key="new-source"><package pattern="Microsoft.PowerShell.Archive"/></packageSource><packageSource key="installed-source"><package pattern="*"/></packageSource></packageSourceMapping>\n' >> "$out/NuGet.config"
fi
printf '</configuration>\n' >> "$out/NuGet.config"
/clang64/lib/dotnet/dotnet.exe restore "$(cygpath -am "$out/Restore.csproj")" --configfile "$(cygpath -am "$out/NuGet.config")" -v:minimal
module="$out/empty-packages/microsoft.powershell.archive/1.2.6"
/usr/bin/python3 "$here/verify-restored.py" "$out" "$module" "$source"
pester=/clang64/lib/dotnet/tools/powershell-module-test-host/Modules/Pester/Pester.psd1
for culture in en-GB en-US;do
  fixture="$out/upstream-$culture"
  /usr/bin/python3 "$here/prepare-tests.py" "$source" "$fixture" "$module"
  SOURCE_POWERSHELL_TEST_CULTURE=$culture timeout 180 /clang64/bin/powershell-module-test-host \
    "$(cygpath -am "$here/RunUpstream.ps1")" "$(cygpath -am "$pester")" \
    "$(cygpath -am "$module/Microsoft.PowerShell.Archive.psd1")" \
    "$(cygpath -am "$fixture/Tests/Pester.Commands.Cmdlets.Archive.Tests.ps1")" \
    "$(cygpath -am "$fixture/results.json")" "$culture"
done
echo 'PASS source-only NuGet restore and both complete Archive upstream culture runs'
