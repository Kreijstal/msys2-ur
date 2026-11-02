#!/usr/bin/env bash
set -euo pipefail
pacman -Q ${MINGW_PACKAGE_PREFIX}-dotnet-sdk8-servicing
pacman -T "${MINGW_PACKAGE_PREFIX}-dotnet-sdk=8.0.131" "${MINGW_PACKAGE_PREFIX}-dotnet-sdk>=8.0.131-4"
/usr/bin/python3 - <<'PY'
from pathlib import Path
import hashlib,json,os,subprocess
prefix,package_prefix=os.environ['MINGW_PREFIX'],os.environ['MINGW_PACKAGE_PREFIX']
installed=set(subprocess.check_output(['pacman','-Qq'],text=True).splitlines())
assert package_prefix+'-dotnet-sdk' not in installed
root=Path(prefix+'/lib/dotnet');manifest=json.loads(Path(prefix+'/share/doc/dotnet-sdk8-servicing/source-sdk-servicing.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for relative,digest in manifest['unchanged_seed_files'].items():assert sha(Path('/')/relative)==digest,relative
adapt=manifest['sdk_metadata_adaptation'];assert sha(Path('/')/adapt['path'])==adapt['adapted_sha256']
for relative,digest in manifest['replaced_host_files'].items():assert sha(root/'packs/Microsoft.NETCore.App.Host.win-x64/8.0.31'/relative)==digest,relative
for relative,record in manifest['runtime_pack_files'].items():assert sha(root/'packs/Microsoft.NETCore.App.Runtime.win-x64/8.0.31'/relative)==record['sha256'],relative
assert sha(root/'packs/Microsoft.NETCore.App.Runtime.win-x64/8.0.31/data/RuntimeList.xml')==manifest['runtime_list_sha256']
for relative in ['sdk/8.0.131/Microsoft.NETCoreSdk.BundledVersions.props','packs/Microsoft.NETCore.App.Host.win-x64/8.0.31/runtimes/win-x64/native/apphost.exe','packs/Microsoft.NETCore.App.Runtime.win-x64/8.0.31/data/RuntimeList.xml']:
 assert subprocess.check_output(['pacman','-Qqo',str(root/relative)],text=True).strip()==package_prefix+'-dotnet-sdk8-servicing'
print('PASS installed unchanged source SDK component, exact metadata adaptation, source host/runtime pack bytes and replacement package ownership')
PY
exec bash ${MINGW_PREFIX}/share/doc/dotnet-sdk8-servicing/check-packs.sh ${MINGW_PREFIX}/lib/dotnet "${1:?usage: check-installed.sh NEW_OUTPUT}"
