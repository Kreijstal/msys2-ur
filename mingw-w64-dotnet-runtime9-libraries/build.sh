#!/usr/bin/env bash
set -euo pipefail
out=$(cd "${1:?usage: build.sh PREPARED_OUTPUT}" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "${RUNTIME9_NS20_CACHE:-$out/cache}")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
/usr/bin/python3 "$(dirname "$0")/refresh-generator-config.py" "$out"
for name in Microsoft.Interop.SourceGeneration Microsoft.Interop.LibraryImportGenerator; do
 /clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/bootstrap/$name/Build.csproj")" -c Release \
  --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal > "$out/bootstrap/$name/build.log" 2>&1
 printf 'PASS complete source9 interop bootstrap: %s\n' "$name"
done
for name in System.Composition.AttributedModel System.Composition.Runtime System.Composition.Hosting System.Composition.Convention System.Composition.TypedParts;do
 /clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/baseline-net8/$name/Build.csproj")" -c Release \
  --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal > "$out/baseline-net8/$name/build.log" 2>&1
 printf 'PASS original NET8 MEF implementation and independent API baseline: %s\n' "$name"
done
name=Microsoft.Bcl.AsyncInterfaces
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/forwarder-netstandard21/$name/Build.csproj")" -c Release \
 --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal > "$out/forwarder-netstandard21/$name/build.log" 2>&1
printf 'PASS original Standard2.1 forwarding target: %s\n' "$name"
for name in System.Collections.Immutable System.Reflection.Metadata System.Composition.AttributedModel System.Composition.Runtime System.Composition.Hosting System.Composition.Convention System.Composition.TypedParts Microsoft.Bcl.AsyncInterfaces System.IO.Pipelines System.Threading.Channels System.Text.Encoding.CodePages; do
 /clang64/lib/dotnet/dotnet.exe pack "$(cygpath -am "$out/libraries/$name/Build.csproj")" -c Release \
  --configfile "$(cygpath -am "$out/NuGet.config")" -o "$(cygpath -am "$out/feed")" -p:UseSharedCompilation=false -v:minimal > "$out/libraries/$name/build.log" 2>&1
 if [[ $name == System.Composition.* ]];then /usr/bin/python3 "$(dirname "$0")/merge-net8.py" "$out" "$name";fi
 if [[ $name == Microsoft.Bcl.AsyncInterfaces ]];then /usr/bin/python3 "$(dirname "$0")/merge-forwarder21.py" "$out";fi
 /usr/bin/python3 "$(dirname "$0")/normalize-maintenance-minimums.py" "$out" "$name"
 printf 'PASS original netstandard2.0 source9 package: %s\n' "$name"
done
/usr/bin/python3 - "$out" <<'PY'
from pathlib import Path
import sys,zipfile
out=Path(sys.argv[1]);source=out/'runtime-source'
with zipfile.ZipFile(out/'feed/System.Composition.9.0.0.nupkg','w',zipfile.ZIP_DEFLATED) as z:
 z.write(out/'System.Composition.nuspec','System.Composition.nuspec')
 z.writestr('lib/netstandard2.0/_._','')
 z.writestr('lib/net8.0/_._','')
 for name in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:
  if (source/name).is_file():z.write(source/name,name)
print('PASS original composition metapackage graph')
PY
