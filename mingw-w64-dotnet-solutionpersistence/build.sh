#!/usr/bin/env bash
set -euo pipefail
out=$(cd "${1:?missing prepared}" && pwd)
source="$out/source/vs-solutionpersistence-19c3ca7dc997dba2b3a86f6c666e9f717f34c8fe"
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export MSBuildEnableWorkloadResolver=false DOTNET_CLI_TELEMETRY_OPTOUT=1
export MSBuildSDKsPath=$(cygpath -am /clang64/lib/dotnet/sdk/8.0.131/Sdks)
export MSBUILD_EXE_PATH=$(cygpath -am /clang64/lib/dotnet/sdk/8.0.131/MSBuild.dll)
mkdir -p "$out/feed" "$out/capture"
/clang64/lib/dotnet/dotnet.exe exec "$(cygpath -am /clang64/lib/dotnet/sdk/8.0.131/MSBuild.dll)" \
  "$(cygpath -am "$source/src/Microsoft.VisualStudio.SolutionPersistence/Microsoft.VisualStudio.SolutionPersistence.csproj")" \
  '-t:Restore;Pack' -p:Configuration=Release -p:SourceBuild=true -p:TargetFrameworks=net8.0 \
  -p:Version=1.0.52 -p:SourceRevisionId=19c3ca7dc997dba2b3a86f6c666e9f717f34c8fe \
  -p:RepositoryCommit=19c3ca7dc997dba2b3a86f6c666e9f717f34c8fe \
  -p:CscToolPath="$(cygpath -am /clang64/lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap)" -p:CscToolExe=csc53.cmd \
  -p:UseSharedCompilation=false -p:EnableNETAnalyzers=false -p:NuGetAudit=false \
  -p:RestoreConfigFile="$(cygpath -am "$out/NuGet.config")" \
  -p:PackageOutputPath="$(cygpath -am "$out/feed")" \
  -p:CustomAfterMicrosoftCommonTargets="$(cygpath -am "$out/Capture.targets")" \
  -p:CaptureRoot="$(cygpath -am "$out/capture")" -v:minimal > "$out/build.log" 2>&1
