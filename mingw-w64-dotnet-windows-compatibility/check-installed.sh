#!/usr/bin/env bash
set -euo pipefail
doc=/clang64/share/doc/dotnet-windows-compatibility
pacman -Q mingw-w64-clang-x86_64-dotnet-windows-compatibility
/usr/bin/python3 - <<'PY'
from pathlib import Path
import hashlib,json,subprocess
doc=Path('/clang64/share/doc/dotnet-windows-compatibility');package=Path('/clang64/lib/dotnet/library-packs/microsoft.windows.compatibility.8.0.31.nupkg')
expected=json.loads((doc/'package-audit.json').read_text())
assert hashlib.sha256(package.read_bytes()).hexdigest()==expected['package_sha256']
assert subprocess.check_output(['pacman','-Qqo',str(package)],text=True).strip()=='mingw-w64-clang-x86_64-dotnet-windows-compatibility'
print('PASS installed source metapackage bytes and native feed ownership')
PY
exec bash "$doc/check.sh" "$doc" "${1:?usage: check-installed.sh NEW_OUTPUT}" /clang64/lib/dotnet/library-packs
