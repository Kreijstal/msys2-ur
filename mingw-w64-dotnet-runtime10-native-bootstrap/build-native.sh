#!/usr/bin/env bash
set -euo pipefail
root=$(cd "${1:?ARCHIVE_ROOT OUTPUT [JOBS]}" && pwd)
out=${2:?OUTPUT}
mkdir -p "$out"
out=$(cd "$out" && pwd)
/usr/bin/python3 "$(dirname "$0")/prepare-native.py" "$root" "$out"
cmake -G Ninja -S "$out/source" -B "$out/build" \
 -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
 -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_RC_COMPILER=llvm-windres \
 -DCLR_CMAKE_HOST_ARCH=x64 -DCLR_CMAKE_TARGET_ARCH=x64 -DCLR_CMAKE_TARGET_OS=windows \
 -DCLI_CMAKE_FALLBACK_OS=win -DCLI_CMAKE_PKG_RID=win-x64 \
 -DCLI_CMAKE_COMMIT_HASH=081d220c0a773ffb7c6bea6b48727833576a65ef \
 -DCLI_CMAKE_RESOURCE_DIR="$root/host-resources" \
 -DCLR_CMAKE_USE_SYSTEM_ZLIB=OFF -DCLR_CMAKE_USE_SYSTEM_BROTLI=OFF \
 -DPython_EXECUTABLE="$(cygpath -am /clang64/bin/python.exe)" \
 -DPython3_EXECUTABLE="$(cygpath -am /clang64/bin/python.exe)" \
 > "$out/configure.log" 2>&1
ninja -C "$out/build" -j"${3:-2}" System.IO.Compression.Native System.Globalization.Native > "$out/build.log" 2>&1
printf '%s\n' 'PASS original Windows native compression and globalization targets built; execution and provenance checks remain required'
