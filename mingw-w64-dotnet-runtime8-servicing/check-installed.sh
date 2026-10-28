#!/usr/bin/env bash
# Fresh SDK consumer and byte gates after installing the audited source package.
set -euo pipefail
mkdir "${1:?usage: check-installed.sh NEW_OUTPUT}"; out=$(cd "$1" && pwd)
doc=/clang64/share/doc/dotnet-runtime8-servicing
export PATH=/clang64/bin:/usr/bin:$PATH
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_MULTILEVEL_LOOKUP=0 DOTNET_CLI_TELEMETRY_OPTOUT=1
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export MSBuildEnableWorkloadResolver=false POWERSHELL_TELEMETRY_OPTOUT=1
pacman -Q mingw-w64-clang-x86_64-dotnet-runtime8-servicing
/usr/bin/python3 - "$doc" <<'PY'
from pathlib import Path
import hashlib,json,sys
doc=Path(sys.argv[1]);manifest=json.loads((doc/'source-payload.json').read_text());checked=0
for name,digest in manifest['files'].items():
 if name.startswith(('shared/Microsoft.NETCore.App/8.0.31/','host/fxr/8.0.31/')):
  path=Path('/clang64/lib/dotnet')/name
  assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,path
  checked+=1
assert checked==176,checked
assert json.loads((doc/'version-build-inputs.json').read_text())['file_version']=='8.0.3126.42000'
print('PASS all176 installed versioned runtime/hostfxr payload files match audited source-build bytes')
PY
cp "$doc/RuntimeCheck.cs" "$out/Program.cs"
cat > "$out/Check.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors></PropertyGroup></Project>
XML
cat > "$out/NuGet.config" <<XML
<configuration><packageSources><clear/><add key="installed-source" value="$(cygpath -am /clang64/lib/dotnet/library-packs)"/></packageSources></configuration>
XML
/clang64/lib/dotnet/dotnet.exe --info
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/Check.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
timeout 180 /clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$out/bin/Release/net8.0/Check.dll")" \
 "$(cygpath -am /clang64/lib/dotnet/shared/Microsoft.NETCore.App/8.0.31)" "$(cygpath -am "$doc/required-framework.txt")"
timeout 180 /clang64/lib/dotnet/dotnet.exe exec --fx-version 8.0.31 \
 /clang64/lib/dotnet/tools/powershell-module-test-host/SourcePowerShell.ModuleHost.dll "$(cygpath -am "$doc/PowerShellCheck.ps1")"
bash "$doc/check-framework-forwarders.sh" /clang64/lib/dotnet "$out/forwarder-check"
echo 'PASS fresh installed serviced runtime, default SDK build/run and original source PowerShell integration'
