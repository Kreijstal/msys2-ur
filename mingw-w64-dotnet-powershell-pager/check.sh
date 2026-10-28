#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
out=${1:?usage: check.sh NEW_OUTPUT PINNED_SOURCE [NEW_FEED]}
source=$(cd "${2:?missing pinned source}" && pwd)
mkdir "$out";out=$(cd "$out" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
/usr/bin/python3 "$here/prepare-tests.py" "$source" "$out/tests"
cp "$here/Check.cs" "$out/Check.cs"
cat > "$out/Check.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><AssemblyName>test</AssemblyName><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Compile Include="Check.cs"/><Compile Include="tests/*.cs"/><PackageReference Include="Microsoft.PowerShell.Pager" Version="[1.0.0]"/></ItemGroup></Project>
PROJECT
feed=${3:-/clang64/lib/dotnet/library-packs}
printf '<configuration><packageSources><clear/><add key="source-pager" value="%s"/></packageSources></configuration>\n' "$(cygpath -am "$feed")" > "$out/NuGet.config"
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/Check.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
module="$out/empty-packages/microsoft.powershell.pager/1.0.0"
bash "$here/inspect.sh" "$module/lib/net8.0/Microsoft.PowerShell.Pager.dll" "$out/metadata"
/usr/bin/python3 "$here/verify-restored.py" "$out" "$module" "$source" "$out/metadata"
timeout 60 /clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$out/bin/Release/net8.0/test.dll")"
