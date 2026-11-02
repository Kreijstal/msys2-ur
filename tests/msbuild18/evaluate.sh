#!/usr/bin/env bash
set -euo pipefail
plan=$(cd "${1:?missing plan}" && pwd)
tool=${2:?missing source evaluation tool DLL}
sdk=$(cygpath -am /clang64/lib/dotnet/sdk/8.0.131)
export MSBuildSDKsPath="$sdk/Sdks" MSBUILD_EXE_PATH="$sdk/MSBuild.dll" MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
/clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$tool")" "$(cygpath -am "$plan/wrappers.json")" "$(cygpath -am "$plan/evaluated.json")"
