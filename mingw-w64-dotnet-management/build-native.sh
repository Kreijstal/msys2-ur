#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
out=${1:?usage: build-native.sh OUTPUT_DIRECTORY}
mkdir -p "$out"
# UCRT64 clang links the GCC runtime; keep winpthread/libstdc++ out of the imports.
static=(); [[ ${MSYSTEM:-} != UCRT64 ]] || static=(-static)
${MINGW_PREFIX}/bin/clang++ -std=c++17 -shared -O2 -Wall -Wextra -Werror \
  "$here/wmi-native.cpp" -o "$out/msys-wmi-native.dll" \
  -lole32 -loleaut32 -lwbemuuid -ladvapi32 -luuid -static-libstdc++ -static-libgcc "${static[@]}"
/usr/bin/python3 "$here/check-native.py" "$out/msys-wmi-native.dll"
