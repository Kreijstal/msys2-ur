#!/usr/bin/env bash
set -euo pipefail
prepared=${1:?usage: build-library.sh PREPARED_ROOT ID FEED}
id=${2:?missing library ID}
feed=${3:?missing feed}
prepared=$(cd "$prepared" && pwd)
mkdir -p "$feed"
feed=$(cd "$feed" && pwd)
dotnet=/clang64/lib/dotnet/dotnet.exe
config=$(cygpath -m "$prepared/NuGet.config")
if [[ $id == System.Diagnostics.EventLog ]]; then
  mkdir "$prepared/$id/messages"
  (
    cd "$prepared/$id/messages"
    # Discarded upstream .res is rebuilt from text. GNU windmc produces the RC
    # and message table; llvm-rc emits the resource consumed by source-built csc.
    /usr/bin/windmc -a -U -n ../../../runtime-8.0.31/src/libraries/System.Diagnostics.EventLog/src/Messages/EventLogMessages.mc
    cp ../../../runtime-8.0.31/src/libraries/System.Diagnostics.EventLog/src/Messages/EventLogMessages.rc .
    MSYS2_ARG_CONV_EXCL='*' /clang64/bin/llvm-rc.exe /FO EventLogMessages.res EventLogMessages.rc
    cat > Messages.csproj <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><AssemblyName>System.Diagnostics.EventLog.Messages</AssemblyName><AssemblyVersion>8.0.0.0</AssemblyVersion><Win32Resource>EventLogMessages.res</Win32Resource><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><SignAssembly>true</SignAssembly><PublicSign>true</PublicSign><AssemblyOriginatorKeyFile>../Library.public.snk</AssemblyOriginatorKeyFile></PropertyGroup></Project>
PROJECT
    "$dotnet" build "$(cygpath -m "$prepared/$id/messages/Messages.csproj")" -c Release --configfile "$config" -p:UseSharedCompilation=false -v:minimal
  )
fi
"$dotnet" build "$(cygpath -m "$prepared/$id/contract/Contract.csproj")" -c Release --configfile "$config" -p:UseSharedCompilation=false -v:minimal
"$dotnet" pack "$(cygpath -m "$prepared/$id/Library.csproj")" -c Release -o "$(cygpath -m "$feed")" --configfile "$config" \
  -p:GeneratePackageOnBuild=false -p:ImportDirectoryBuildProps=false -p:ImportDirectoryBuildTargets=false -p:UseSharedCompilation=false -v:minimal
