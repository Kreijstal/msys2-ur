#!/usr/bin/env bash
set -euo pipefail
root=$(cd "${1:?usage: build-corerun.sh ARCHIVE_ROOT}" && pwd)
here=$(cd "$(dirname "$0")" && pwd)
patch --forward --fuzz=0 --no-backup-if-mismatch -d "$root/r" -p1 -i "$here/corerun-mingw.patch" >"$root/corerun-patch.log" 2>&1
cmake -G Ninja -S "$root/r/src/coreclr" -B "$root/coreclr-build" \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_RC_COMPILER=llvm-windres -DCMAKE_ASM_MASM_COMPILER=uasm \
  -DCMAKE_INSTALL_PREFIX="$root/coreclr" \
  -DCLR_CMAKE_HOST_ARCH=x64 -DCLR_CMAKE_TARGET_ARCH=x64 -DCLR_CMAKE_TARGET_OS=windows \
  -DCLI_CMAKE_FALLBACK_OS=win -DCLI_CMAKE_PKG_RID=win-x64 \
  -DCLI_CMAKE_COMMIT_HASH=081d220c0a773ffb7c6bea6b48727833576a65ef \
  -DCLI_CMAKE_RESOURCE_DIR="$root/host-resources" \
  -DCLR_CMAKE_PGO_INSTRUMENT=0 -DCLR_CMAKE_PGO_OPTIMIZE=0 \
  -DCLR_CMAKE_KEEP_NATIVE_SYMBOLS=ON \
  -DPython_EXECUTABLE="$(cygpath -am /clang64/bin/python.exe)" \
  -DPython3_EXECUTABLE="$(cygpath -am /clang64/bin/python.exe)" \
  > "$root/coreclr-configure.log" 2>&1
ninja -C "$root/coreclr-build" -j"${2:-2}" corerun \
  > "$root/coreclr-build.log" 2>&1
"$root/coreclr-build/hosts/corerun/corerun.exe" -st >"$root/corerun-selftest.log" 2>&1
