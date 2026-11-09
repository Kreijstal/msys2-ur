#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check-native-abi.sh NEW_OUTPUT [FEED] [--baseline]}"
out=$(cd "$1" && pwd)
export DOTNET_ROOT=$(cygpath -am "$MINGW_PREFIX/lib/dotnet") DOTNET_ROOT_X64=$(cygpath -am "$MINGW_PREFIX/lib/dotnet")
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
cp "$here/NativeAbiChecks.cs" "$out/Program.cs"
cat > "$out/Inspect.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><TreatWarningsAsErrors>true</TreatWarningsAsErrors></PropertyGroup></Project>
XML
printf '<configuration><packageSources><clear/></packageSources></configuration>\n' > "$out/NuGet.config"
"$MINGW_PREFIX/lib/dotnet/dotnet.exe" build "$(cygpath -am "$out/Inspect.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
feed=${2:-$MINGW_PREFIX/lib/dotnet/library-packs}
/usr/bin/python3 - "$feed" "$out" "${MMI_ABI_ASSEMBLY:-}" <<'PYCODE'
from pathlib import Path
import sys,zipfile,hashlib,json
feed,out=map(Path,sys.argv[1:3]);archive=next(p for p in feed.iterdir() if p.name.lower()=='microsoft.management.infrastructure.3.0.0.nupkg')
with zipfile.ZipFile(archive) as z:dll=z.read('lib/net8.0/Microsoft.Management.Infrastructure.dll')
if sys.argv[3]:assert Path(sys.argv[3]).read_bytes()==dll
(out/'source-mmi.dll').write_bytes(dll)
(out/'identity.json').write_text(json.dumps({'feed_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'implementation_sha256':hashlib.sha256(dll).hexdigest(),'explicit_bundle_identity_verified':bool(sys.argv[3])},indent=2)+'\n')
PYCODE
"$MINGW_PREFIX/bin/clang" -std=c11 -shared -Wall -Wextra -Werror "$here/check-native-abi.c" -o "$out/binding-probe.dll"
"$MINGW_PREFIX/lib/dotnet/dotnet.exe" "$(cygpath -am "$out/bin/Release/net8.0/Inspect.dll")" "$(cygpath -am "$out/source-mmi.dll")" "$(cygpath -am "$out/managed-schema.json")" "$(cygpath -am "$out/binding-probe.dll")"
/usr/bin/python3 "$here/capture-native-abi.py" "$MINGW_PREFIX" "$out"
/usr/bin/python3 "$here/generate-native-abi.py" "$out/managed-schema.json" "$out/native-probe.c"
"$MINGW_PREFIX/bin/clang" -std=c11 -Wall -Wextra -Werror "$out/native-probe.c" -o "$out/native-probe.exe"
"$out/native-probe.exe" > "$out/native-layout.json"
/usr/bin/python3 "$here/compare-native-abi.py" "$out/native-schema.json" "$out/native-layout.json" "$out/managed-schema.json" "$out/results.json" "${@:3}"
