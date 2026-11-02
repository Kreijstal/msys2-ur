#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
consumer=$(cd "${1:?usage: check-api.sh CONSUMER NEW_OUTPUT}" && pwd)
mkdir "${2:?missing output}";out=$(cd "$2" && pwd)
cp "$here/InspectApi.cs" "$out/Program.cs"
cat > "$out/Inspect.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.CodeAnalysis.CSharp" Version="[4.9.2]"/></ItemGroup></Project>
PROJECT
cat > "$out/NuGet.config" <<CONFIG
<configuration><packageSources><clear/><add key="source-built-tools" value="$(cygpath -m ${MINGW_PREFIX}/lib/dotnet/library-packs)"/></packageSources></configuration>
CONFIG
export DOTNET_ROOT=$(cygpath -m ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$out/cli-home") NUGET_PACKAGES=$(cygpath -m "$out/empty-packages")
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -m "$out/Inspect.csproj")" -c Release --configfile "$(cygpath -m "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -m "$out/bin/Release/net8.0/Inspect.dll")" \
 "$(cygpath -m ${MINGW_PREFIX}/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0)" \
 "$(cygpath -m "$consumer/bin/Release/net8.0/CommonMark.dll")" > "$out/actual-api.json"
/usr/bin/python3 - "$here/ExpectedApi.json" "$out/actual-api.json" <<'PY'
import json,sys
expected,actual=(json.load(open(p)) for p in sys.argv[1:])
assert actual['identity']==expected['identity'],(actual['identity'],expected['identity'])
wanted=set(expected['api']);got=set(actual['api']);extra=set()
missing=wanted-got;unexpected=got-wanted-extra;stale=extra-got
for label,values in [('MISSING',missing),('UNEXPECTED',unexpected),('STALE EXCEPTION',stale)]:
 for value in sorted(values):print(label,value)
assert not (missing or unexpected or stale)
print('PASS all '+str(len(wanted))+' published CommonMark.NET public/protected declarations and exact assembly identity')
PY
