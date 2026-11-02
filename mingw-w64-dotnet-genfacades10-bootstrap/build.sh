#!/usr/bin/env bash
set -euo pipefail
root=$(cd "${1:?ARCHIVE_ROOT}" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$root/build/cli-home") NUGET_PACKAGES=$(cygpath -am "$root/build/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$root/build/Build.csproj")" -c Release --configfile "$(cygpath -am "$root/build/NuGet.config")" -p:UseSharedCompilation=false -v:minimal >"$root/build.log" 2>&1
mkdir -p "$root/product/tools/net" "$root/product/build"
/usr/bin/python3 - "$root" <<'PY_STAGE'
from pathlib import Path
import shutil,sys
root=Path(sys.argv[1]);source=root/'build/bin/Release/net8.0';target=root/'product/tools/net'
for p in source.rglob('*.dll'):
 out=target/p.relative_to(source);out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,out)
PY_STAGE
cp "$root/build/bin/Release/net8.0/Microsoft.DotNet.GenFacades.deps.json" "$root/product/tools/net/"
cp "$root/arcade/src/Microsoft.DotNet.GenFacades/build/"*.targets "$root/product/build/"
