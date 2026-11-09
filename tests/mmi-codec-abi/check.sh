#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check.sh NEW_OUTPUT}"
out=$(cd "$1" && pwd)
export DOTNET_ROOT=$(cygpath -am "$MINGW_PREFIX/lib/dotnet") DOTNET_ROOT_X64=$(cygpath -am "$MINGW_PREFIX/lib/dotnet")
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
cp "$here/InspectCodec.cs" "$out/Program.cs"
cat > "$out/Inspect.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><TreatWarningsAsErrors>true</TreatWarningsAsErrors></PropertyGroup></Project>
XML
printf '<configuration><packageSources><clear/></packageSources></configuration>\n' > "$out/NuGet.config"
"$MINGW_PREFIX/lib/dotnet/dotnet.exe" build "$(cygpath -am "$out/Inspect.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
/usr/bin/python3 - "$MINGW_PREFIX" "$out" <<'PY'
from pathlib import Path
import sys,zipfile,hashlib,json,subprocess
prefix,out=map(Path,sys.argv[1:]);feed=prefix/'lib/dotnet/library-packs/microsoft.management.infrastructure.3.0.0.nupkg';dll=prefix/'lib/powershell/7/Microsoft.Management.Infrastructure.dll'
with zipfile.ZipFile(feed) as z:assert z.read('lib/net8.0/Microsoft.Management.Infrastructure.dll')==dll.read_bytes()
package_prefix='mingw-w64-'+('clang-x86_64' if prefix.name=='clang64' else 'ucrt-x86_64')
packages=subprocess.check_output(['pacman','-Q',package_prefix+'-dotnet-mmi3',package_prefix+'-powershell',package_prefix+'-dotnet-sqlclient'],text=True).splitlines()
(out/'identity.json').write_text(json.dumps({'feed_sha256':hashlib.sha256(feed.read_bytes()).hexdigest(),'bundled_mmi_sha256':hashlib.sha256(dll.read_bytes()).hexdigest(),'source_archive_and_bundle_match':True,'installed_packages':packages},indent=2)+'\n')
PY
"$MINGW_PREFIX/lib/dotnet/dotnet.exe" "$(cygpath -am "$out/bin/Release/net8.0/Inspect.dll")" "$(cygpath -am "$MINGW_PREFIX/lib/powershell/7/Microsoft.Management.Infrastructure.dll")" "$(cygpath -am "$out/managed-schema.json")"
/usr/bin/python3 "$here/capture.py" "$MINGW_PREFIX" "$out"
/usr/bin/python3 "$here/compare.py" "$out"
