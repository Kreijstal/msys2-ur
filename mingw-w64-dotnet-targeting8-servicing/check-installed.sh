#!/usr/bin/env bash
# Read installed ownership and compile using normal SDK targeting-pack selection.
set -euo pipefail
mkdir "${1:?usage: check-installed.sh NEW_OUTPUT}"; out=$(cd "$1" && pwd)
export PATH=${MINGW_PREFIX}/bin:/usr/bin:$PATH
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false DOTNET_MULTILEVEL_LOOKUP=0
pacman -Q ${MINGW_PACKAGE_PREFIX}-dotnet-targeting8-servicing
pacman -T "${MINGW_PACKAGE_PREFIX}-dotnet-targeting-pack=8.0.131" "${MINGW_PACKAGE_PREFIX}-dotnet-targeting-pack>=8.0.131-2"
/usr/bin/python3 - <<'PY'
from pathlib import Path
import hashlib,json,os,subprocess
installed=set(subprocess.check_output(['pacman','-Qq'],text=True).splitlines())
assert os.environ['MINGW_PACKAGE_PREFIX']+'-dotnet-targeting-pack' not in installed,'Old package remains installed alongside its replacement'
pack=Path(os.environ['MINGW_PREFIX']+'/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31')
manifest=json.loads((pack/'source-payload.json').read_text())
assert len(manifest['files'])==595
for relative,record in manifest['files'].items():
 assert hashlib.sha256((pack/relative).read_bytes()).hexdigest()==record['sha256'],relative
for name,key in [('FrameworkList.xml','framework_list_sha256'),('PlatformManifest.txt','platform_manifest_sha256'),('PackageOverrides.txt','original_package_overrides_sha256')]:
 assert hashlib.sha256((pack/'data'/name).read_bytes()).hexdigest()==manifest[key],name
assert hashlib.sha256((pack/'source-platform-manifest.json').read_bytes()).hexdigest()==manifest['platform_manifest_source_proof_sha256']
assert manifest['platform_manifest_unique_entries']==342
for relative in ['ref/net8.0/System.Runtime.dll','analyzers/dotnet/cs/Microsoft.Interop.ComInterfaceGenerator.dll','data/PlatformManifest.txt']:
 owner=subprocess.check_output(['pacman','-Qqo',str(pack/relative)],text=True).strip()
 assert owner==os.environ['MINGW_PACKAGE_PREFIX']+'-dotnet-targeting8-servicing',owner
print('PASS installed595 DLL payload bytes, complete manifest and replacement native-package ownership')
PY
cp ${MINGW_PREFIX}/share/doc/dotnet-targeting8-servicing/SdkGeneratorCheck.cs "$out/Program.cs"
cat > "$out/Check.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk">
 <PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><AllowUnsafeBlocks>true</AllowUnsafeBlocks><Nullable>enable</Nullable><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><JsonSerializerIsReflectionEnabledByDefault>false</JsonSerializerIsReflectionEnabledByDefault><TreatWarningsAsErrors>true</TreatWarningsAsErrors></PropertyGroup>
 <Target Name="RecordNormalInstalledSelection" BeforeTargets="CoreCompile">
  <WriteLinesToFile File="$(IntermediateOutputPath)analyzers.txt" Lines="@(Analyzer->'%(FullPath)')" Overwrite="true" Encoding="UTF-8"/>
  <WriteLinesToFile File="$(IntermediateOutputPath)references.txt" Lines="@(ReferencePathWithRefAssemblies->'%(FullPath)')" Overwrite="true" Encoding="UTF-8"/>
  <WriteLinesToFile File="$(IntermediateOutputPath)compiler.txt" Lines="$(CscToolPath)|$(CscToolExe)" Overwrite="true" Encoding="UTF-8"/>
 </Target>
</Project>
XML
cat > "$out/NuGet.config" <<XML
<configuration><packageSources><clear/><add key="installed-source" value="$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/library-packs)"/></packageSources></configuration>
XML
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/Check.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
timeout 90 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/bin/Release/net8.0/Check.dll")"
/usr/bin/python3 - "$out/obj/Release/net8.0" <<'PY'
from pathlib import Path
import hashlib,json,os,subprocess,sys
folder=Path(sys.argv[1]);pack=Path(os.environ['MINGW_PREFIX']+'/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31')
manifest=json.loads((pack/'source-payload.json').read_text())
prefix=subprocess.check_output(['cygpath','-am',str(pack)],text=True).strip().replace('\\','/')+'/'
references=(folder/'references.txt').read_text(encoding='utf-8-sig').splitlines()
analyzers=(folder/'analyzers.txt').read_text(encoding='utf-8-sig').splitlines()
assert len(references)==163,len(references)
for line in references:
 line=line.replace('\\','/');assert line.lower().startswith(prefix.lower()),line
 relative=line[len(prefix):];assert hashlib.sha256((pack/relative).read_bytes()).hexdigest()==manifest['files'][relative]['sha256']
for name in ['Microsoft.Interop.SourceGeneration','Microsoft.Interop.LibraryImportGenerator','Microsoft.Interop.ComInterfaceGenerator','Microsoft.Interop.JavaScript.JSImportGenerator','System.Text.RegularExpressions.Generator','System.Text.Json.SourceGeneration']:
 selected=[p.replace('\\','/') for p in analyzers if Path(p.replace('\\','/')).name==name+'.dll']
 assert len(selected)==1 and selected[0].lower().startswith(prefix.lower()),(name,selected)
compiler=(folder/'compiler.txt').read_text(encoding='utf-8-sig').replace('\\','/').strip()
assert 'compiler-packs/roslyn-4.9.2' in compiler and compiler.endswith('|csc49.cmd'),compiler
print('PASS installed source SDK selects163 serviced references and six generators normally; default compiler4.9, COM/PInvoke/Regex/JSON execution')
PY
