#!/usr/bin/env bash
set -euo pipefail
pacman -Q mingw-w64-clang-x86_64-dotnet-sdk8-servicing
pacman -T 'mingw-w64-clang-x86_64-dotnet-sdk=8.0.131' 'mingw-w64-clang-x86_64-dotnet-sdk>=8.0.131-3'
/usr/bin/python3 - <<'PY'
from pathlib import Path
import hashlib,json,subprocess
installed=set(subprocess.check_output(['pacman','-Qq'],text=True).splitlines())
assert 'mingw-w64-clang-x86_64-dotnet-sdk' not in installed
root=Path('/clang64/lib/dotnet');manifest=json.loads(Path('/clang64/share/doc/dotnet-sdk8-servicing/source-sdk-servicing.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for relative,digest in manifest['unchanged_seed_files'].items():assert sha(Path('/')/relative)==digest,relative
adapt=manifest['sdk_metadata_adaptation'];assert sha(Path('/')/adapt['path'])==adapt['adapted_sha256']
for relative,digest in manifest['replaced_host_files'].items():assert sha(root/'packs/Microsoft.NETCore.App.Host.win-x64/8.0.31'/relative)==digest,relative
for relative,record in manifest['runtime_pack_files'].items():assert sha(root/'packs/Microsoft.NETCore.App.Runtime.win-x64/8.0.31'/relative)==record['sha256'],relative
assert sha(root/'packs/Microsoft.NETCore.App.Runtime.win-x64/8.0.31/data/RuntimeList.xml')==manifest['runtime_list_sha256']
for relative in ['sdk/8.0.131/Microsoft.NETCoreSdk.BundledVersions.props','packs/Microsoft.NETCore.App.Host.win-x64/8.0.31/runtimes/win-x64/native/apphost.exe','packs/Microsoft.NETCore.App.Runtime.win-x64/8.0.31/data/RuntimeList.xml']:
 assert subprocess.check_output(['pacman','-Qqo',str(root/relative)],text=True).strip()=='mingw-w64-clang-x86_64-dotnet-sdk8-servicing'
print('PASS installed unchanged source SDK component, exact metadata adaptation, source host/runtime pack bytes and replacement package ownership')
PY
exec bash /clang64/share/doc/dotnet-sdk8-servicing/check-packs.sh /clang64/lib/dotnet "${1:?usage: check-installed.sh NEW_OUTPUT}"
