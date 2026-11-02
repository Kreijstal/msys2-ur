#!/usr/bin/env bash
set -euo pipefail
out=$(cd "${1:?usage: build.sh PREPARED_ROOT}" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export GITHUB_EVENT_NAME=push GITHUB_REF_NAME=rel/1.15.0
# Run outside upstream global.json so the explicit source SDK8 bootstrap is used.
cd "$out"
cat > "$out/NuGet.config" <<CONFIG
<configuration><packageSources><clear/><add key="installed-source" value="$(cygpath -am /clang64/lib/dotnet/library-packs)"/></packageSources></configuration>
CONFIG
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/source/src/PolySharp.Package/PolySharp.Package.msbuildproj")" -c Release \
  --configfile "$(cygpath -am "$out/NuGet.config")" \
  -p:CscToolPath="$(cygpath -am /clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap)" -p:CscToolExe=csc50.cmd \
  -p:UseSharedCompilation=false -p:DirectoryBuildTargetsPath="$(cygpath -am "$out/Capture.targets")" \
  -p:PackageOutputPath="$(cygpath -am "$out/feed")" -p:RepositoryCommit=02753db24d9685e54db06739eb63183d86eb5b62 -v:minimal
