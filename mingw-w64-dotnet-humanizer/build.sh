#!/usr/bin/env bash
set -euo pipefail
out=$(cd "${1:?usage: build.sh PREPARED_OUTPUT}" && pwd)
source="$out/Humanizer-3ebc38de585fc641a04b0e78ed69468453b0f8a1"
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
for tfm in netstandard2.0 net8.0;do
 /clang64/lib/dotnet/dotnet.exe pack "$(cygpath -am "$source/src/Humanizer/Humanizer.csproj")" \
  -c Release -o "$(cygpath -am "$out/packages/$tfm")" --configfile "$(cygpath -am "$out/NuGet.config")" \
  -p:TargetFrameworks="$tfm" -p:TargetFramework="$tfm" \
  -p:BaseIntermediateOutputPath="$(cygpath -am "$out/obj/$tfm")/" \
  -p:MSBuildProjectExtensionsPath="$(cygpath -am "$out/obj/$tfm")/" \
  -p:ImportDirectoryBuildProps=false -p:ImportDirectoryBuildTargets=false \
  -p:CustomAfterMicrosoftCommonTargets="$(cygpath -am "$out/PackageAssets.targets")" \
  -p:PackageId=Humanizer.Core -p:PackageVersion=2.14.1 -p:Version=2.14.1 \
  -p:AssemblyVersion=2.14.0.0 -p:FileVersion=2.14.1.0 \
  -p:InformationalVersion=2.14.1+3ebc38de585fc641a04b0e78ed69468453b0f8a1 \
  -p:IncludeSourceRevisionInInformationalVersion=false \
  -p:PublishRepositoryUrl=true -p:EmbedUntrackedSources=true \
  -p:RepositoryUrl=https://github.com/Humanizr/Humanizer -p:RepositoryCommit=3ebc38de585fc641a04b0e78ed69468453b0f8a1 \
  -p:EnableNETAnalyzers=false -p:NuGetAudit=false -p:UseSharedCompilation=false \
  > "$out/build-$tfm.log" 2>&1
 printf 'PASS unchanged Humanizer sources/project: %s\n' "$tfm"
done
/usr/bin/python3 "$(dirname "$0")/merge.py" "$out"
