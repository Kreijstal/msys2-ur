"""Install a relocatable MSBuild18 bootstrap and its source/provenance checks."""
from pathlib import Path
import hashlib,json,shutil,sys

root,prefix=(Path(p).resolve() for p in sys.argv[1:]);prefix.mkdir()
here=Path(__file__).resolve().parent;tool=prefix/'lib/dotnet10/build-packs/msbuild-18.3.0-net10-bootstrap';tool.parent.mkdir(parents=True)
shutil.copytree(root/'localized/bin',tool)
for p in tool.glob('Check.*'):p.unlink()
doc=prefix/'share/doc/dotnet-msbuild18-bootstrap';doc.mkdir(parents=True)
checks=doc/'checks';checks.mkdir()
for name in ['check-installed.py','check-parallel.py']:shutil.copyfile(here/name,checks/name)
for name in ['Check.dll','Check.runtimeconfig.json']:shutil.copyfile(root/'localized/bin'/name,checks/name)
shutil.copyfile(root/'localized/Check.cs',checks/'Check.cs');shutil.copyfile(root/'localized/expected.json',checks/'expected-resources.json')
for source,target in [('plan/source-inputs.json','source-inputs.json'),('prepare-results.json','prepare-results.json'),('build-results.json','build-results.json'),('build/results.json','managed-build-results.json'),('version/results.json','version-results.json'),('cli/results.json','cli-results.json'),('localized/results.json','localization-results.json'),('parallel/results.json','parallel-results.json'),('source-audit.json','source-audit.json'),('output-audit.json','output-audit.json')]:shutil.copyfile(root/source,doc/target)
shutil.copyfile(here/'README.md',doc/'README.md')
source=Path(json.loads((root/'plan/source-inputs.json').read_text())['source_root'])
license_dir=prefix/'share/licenses/dotnet-msbuild18-bootstrap';license_dir.mkdir(parents=True)
shutil.copyfile(source/'LICENSE',license_dir/'LICENSE')
for name in ['THIRDPARTYNOTICES.txt','THIRD-PARTY-NOTICES.txt']:
    if (source/name).is_file():shutil.copyfile(source/name,license_dir/name)
# Source-package data is compiled into MSBuild. Preserve its licensing too.
import zipfile
for package in (root/'msbuild-source-packages').glob('*.nupkg'):
    with zipfile.ZipFile(package) as z:
        for n in z.namelist():
            if n.lower().endswith(('license.txt','license.md')):
                (license_dir/(package.stem+'-'+Path(n).name)).write_bytes(z.read(n))
bin_dir=prefix/'bin';bin_dir.mkdir()
launcher=bin_dir/'msbuild18-bootstrap'
launcher.write_text('''#!/usr/bin/env bash
set -euo pipefail
prefix=$(cd "$(dirname "$0")/.." && pwd)
export DOTNET_ROOT=$(cygpath -am "$prefix/lib/dotnet10")
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_HOST_PATH="$DOTNET_ROOT/dotnet.exe"
export MSBUILD_EXE_PATH=$(cygpath -am "$prefix/lib/dotnet10/build-packs/msbuild-18.3.0-net10-bootstrap/MSBuild.dll")
export MSBUILDUSESERVER=0 MSBUILDDISABLENODEREUSE=1
exec "$prefix/lib/dotnet10/dotnet.exe" "$MSBUILD_EXE_PATH" "$@"
''',encoding='utf-8',newline='\n');launcher.chmod(0o755)
(tool/'msbuild18-bootstrap.cmd').write_text(r'''@echo off
setlocal
set "DOTNET_ROOT=%~dp0..\..\..\dotnet10"
set "DOTNET_ROOT_X64=%DOTNET_ROOT%"
set "DOTNET_HOST_PATH=%DOTNET_ROOT%\dotnet.exe"
set "MSBUILD_EXE_PATH=%~dp0MSBuild.dll"
set "MSBUILDUSESERVER=0"
set "MSBUILDDISABLENODEREUSE=1"
"%DOTNET_HOST_PATH%" "%MSBUILD_EXE_PATH%" %*
exit /b %errorlevel%
''',encoding='utf-8',newline='\r\n')
manifest={p.relative_to(prefix).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in prefix.rglob('*') if p.is_file()}
(doc/'payload-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PASS staged MSBuild18 bootstrap',len(manifest),'regular payload files')
