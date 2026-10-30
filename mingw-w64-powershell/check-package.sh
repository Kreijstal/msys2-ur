#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
prefix=$(cd "${1:?usage: check-package.sh PREFIX NEW_OUTPUT FIXTURES}" && pwd)
mkdir "${2:?missing output}"; out=$(cd "$2" && pwd)
fixtures=$(cd "${3:?missing fixtures}" && pwd)
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet)
export POWERSHELL_TELEMETRY_OPTOUT=1 DOTNET_CLI_TELEMETRY_OPTOUT=1
/usr/bin/python3 - "$prefix" <<'PY'
from pathlib import Path
import hashlib,json,sys
prefix=Path(sys.argv[1]);doc=prefix/'share/doc/powershell'
manifest=json.loads((doc/'source-package.json').read_text())
owned=[prefix/'bin/pwsh.exe']
for folder in ['lib/powershell/7','share/licenses/powershell','share/doc/powershell']:
 owned.extend(p for p in (prefix/folder).rglob('*') if p.is_file() and p!=doc/'source-package.json')
actual={p.relative_to(prefix).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in owned}
assert actual==manifest['files_sha256']
license=json.loads((doc/'license-closure.json').read_text())
for relative,digest in license['copied_license_files'].items():
 assert hashlib.sha256((prefix/'share/licenses/powershell'/relative).read_bytes()).hexdigest()==digest,relative
assert len(license['bundled_source_native_owners'])>=70
print('PASS complete source distribution file hashes and every declared source/native-owner license')
PY
${MINGW_PREFIX}/bin/python.exe "$(cygpath -am "$here/check-launcher.py")" "$(cygpath -am "$prefix")" "$(cygpath -am "$out/launcher")" --dotnet-root "$(cygpath -am ${MINGW_PREFIX}/lib/dotnet)"
smokes=(Smoke CimWmiSmoke ChildSmoke)
# the desktop smoke ships only with a WindowsDesktop build
[[ ! -f $fixtures/DesktopSmoke.ps1 ]] || smokes+=(DesktopSmoke)
for name in "${smokes[@]}"; do
 args=();[[ $name != DesktopSmoke ]]||args=(-STA)
 [[ $name != CimWmiSmoke ]]||args=(-MTA)
 timeout 180 "$prefix/bin/pwsh.exe" -NoLogo -NoProfile -NonInteractive "${args[@]}" -ExecutionPolicy Bypass -File "$(cygpath -am "$fixtures/$name.ps1")"
done
timeout 180 "$prefix/bin/pwsh.exe" -NoLogo -NoProfile -NonInteractive -STA -ExecutionPolicy Bypass \
 -File "$(cygpath -am "$fixtures/CimWmiSmoke.ps1")"
timeout 60 "$prefix/bin/pwsh.exe" -NoLogo -NoProfile -NonInteractive -STA -ExecutionPolicy Bypass \
 -File "$(cygpath -am "$fixtures/WmiStaProbe.ps1")"
timeout 180 "$prefix/bin/pwsh.exe" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass \
 -File "$(cygpath -am "$fixtures/GallerySmoke.ps1")" -Output "$(cygpath -am "$out/gallery")"
echo "PASS packaged native launcher/full SDK/STA+MTA MMI+CIM+WMI/LocalAccounts/source gallery/native child${smokes[3]:+/source desktop rendering} and license closure"
