#!/usr/bin/env bash
set -euo pipefail
out=$(cd "${1:?usage: build.sh PREPARED_ROOT}" && pwd)
compiler=$(cd "${2:?missing source csc4.4 directory}" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
cat > "$out/NuGet.config" <<CONFIG
<configuration><packageSources><clear/><add key="installed-source" value="$(cygpath -am /clang64/lib/dotnet/library-packs)"/></packageSources></configuration>
CONFIG
cd "$out"
for project in Mono.Cecil.csproj rocks/Mono.Cecil.Rocks.csproj symbols/mdb/Mono.Cecil.Mdb.csproj symbols/pdb/Mono.Cecil.Pdb.csproj; do
  name=$(basename "$project" .csproj)
  /clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/source/$project")" -c Release \
    --configfile "$(cygpath -am "$out/NuGet.config")" -p:TargetFrameworks=netstandard2.0 \
    -p:CscToolPath="$(cygpath -am "$compiler")" -p:CscToolExe=csc44.cmd \
    -p:UseSharedCompilation=false -p:TreatWarningsAsErrors=true \
    -p:DirectoryBuildTargetsPath="$(cygpath -am "$out/Capture.targets")" -p:NuGetAudit=false -v:minimal > "$out/$name.build.log" 2>&1
  printf 'PASS original NS2 project %s\n' "$name"
done
/clang64/lib/dotnet/dotnet.exe pack "$(cygpath -am "$out/source/Mono.Cecil.csproj")" -c Release \
  --configfile "$(cygpath -am "$out/NuGet.config")" -p:TargetFrameworks=netstandard2.0 \
  -p:IsPackable=true -p:NoBuild=true -p:NuspecFile="$(cygpath -am "$out/source/NS2.nuspec")" \
  -p:NuspecBasePath="$(cygpath -am "$out/source")" -p:NuGetAudit=false -o "$(cygpath -am "$out/feed")" -v:minimal
