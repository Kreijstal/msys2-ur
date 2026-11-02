#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
prepared=${1:?usage: check-api.sh PREPARED_ROOT CONSUMER_ROOT NEW_OUTPUT_ROOT}
consumer=${2:?missing consumer root}
out=${3:?missing output root}
mkdir "$out"
out=$(cd "$out" && pwd)
prepared=$(cd "$prepared" && pwd)
consumer=$(cd "$consumer" && pwd)
cp "$here/check-api.cs" "$out/Program.cs"
cat > "$out/check-api.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup></Project>
PROJECT
export DOTNET_ROOT=$(cygpath -m /clang64/lib/dotnet)
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_CLI_HOME=$(cygpath -m "$out/cli-home") NUGET_PACKAGES=$(cygpath -m "$out/empty-packages")
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -m "$out/check-api.csproj")" -c Release --configfile "$(cygpath -m "$prepared/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
while read -r id; do
  /clang64/lib/dotnet/dotnet.exe "$(cygpath -m "$out/bin/Release/net8.0/check-api.dll")" \
    "$(cygpath -m "$prepared/$id/contract/bin/Release/net8.0/$id.dll")" \
    "$(cygpath -m "$consumer/bin/Release/net8.0")" \
    "$(cygpath -m "$consumer/bin/Release/net8.0")"
done < <(/usr/bin/python3 -c 'import json,sys; [print(v["id"]) for v in json.load(open(sys.argv[1]))]' "$here/libraries.json")
