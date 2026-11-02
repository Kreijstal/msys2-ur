#!/usr/bin/env bash
set -euo pipefail
out=$(cd "${1:?missing prepared}" && pwd)
here=$(cd "$(dirname "$0")" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/evaluation-tool/Build.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal > "$out/evaluation-build.log" 2>&1
export MSBuildSDKsPath=$(cygpath -am /clang64/lib/dotnet/sdk/8.0.131/Sdks) MSBUILD_EXE_PATH=$(cygpath -am /clang64/lib/dotnet/sdk/8.0.131/MSBuild.dll)
/clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$out/evaluation-tool/bin/Release/net8.0/Build.dll")" "$(cygpath -am "$out/plan/wrappers.json")" "$(cygpath -am "$out/plan/evaluated.json")" > "$out/evaluate.log" 2>&1
/clang64/bin/python.exe -X utf8 "$(cygpath -am "$here/build-library.py")" "$(cygpath -am "$out/plan")" "$(cygpath -am /clang64/lib/dotnet/reference-packs/runtime-9.0.11/ref/net9.0)" "$(cygpath -am "$out/build")" > "$out/compile.log" 2>&1
/clang64/bin/python.exe -X utf8 "$(cygpath -am "$here/pack.py")" "$(cygpath -am "$out")"
