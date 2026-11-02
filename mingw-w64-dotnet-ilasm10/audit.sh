#!/usr/bin/env bash
set -euo pipefail
root=$(cd "${1:?usage: audit.sh PREPARED_ROOT RUNTIME_ARCHIVE}" && pwd)
archive=${2:?runtime archive required}
here=$(cd "$(dirname "$0")" && pwd)
for mode in prepare verify;do
 if [[ $mode == verify ]];then
  for name in host-mingw.patch coreclr-mingw.patch resource-section-index.patch cetcompat.patch;do
   patch -d "$root/audit-replay" -p1 --fuzz=0 --forward --no-backup-if-mismatch -i "$here/$name" >> "$root/audit-patch-replay.log"
  done
 fi
 /clang64/bin/python.exe "$(cygpath -am "$here/audit-native.py")" "$mode" \
  "$(cygpath -am "$archive")" "$(cygpath -am "$root")" "$(cygpath -am "$here")"
done
