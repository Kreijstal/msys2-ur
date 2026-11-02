#!/usr/bin/env bash
set -euo pipefail
source_root=$(cd "${1:?usage: build-plugin.sh SOURCE OUTPUT}" && pwd)
mkdir -p "${2:?usage: build-plugin.sh SOURCE OUTPUT}"
output=$(cd "$2" && pwd)
native=$source_root/src/powershell-native/nativemsh
cd "$output"
# UCRT64 clang links the GCC runtime (WinRM loads the plugin outside PATH)
# and defaults to GNU ld, which cannot link the .res file.
static=(); [[ ${MSYSTEM:-} != UCRT64 ]] || static=(-static -fuse-ld=lld)
windmc -c -U -h . -r . "$native/pwrshplugin/pwrshpluginerrorcodes.mc"
# llvm-rc treats GNU's MESSAGETABLE keyword as a string resource type.
sed -i 's/ MESSAGETABLE / 11 /' pwrshpluginerrorcodes.rc
MSYS2_ARG_CONV_EXCL='*' llvm-rc /I "$(cygpath -m "$native/pwrshplugin")" \
  /I "$(cygpath -m ${MINGW_PREFIX}/include)" \
  /I "$(cygpath -m "$output")" /FO plugin.res \
  "$(cygpath -m "$native/pwrshplugin/pwrshpluginResources.rc")"
clang++ -std=c++14 -O2 -g -shared -DCORECLR=1 -DUNICODE -D_UNICODE \
  -D_WIN32_WINNT=0x0602 -fms-extensions \
  -I "$native/pwrshcommon" -I "$output" \
  "$native/pwrshcommon/pwrshcommon.cpp" \
  "$native/pwrshcommon/WinSystemCallFacade.cpp" \
  "$native/pwrshcommon/ConfigFileReader.cpp" \
  "$native/pwrshplugin/entrypoints.cpp" \
  "$native/pwrshplugin/pwrshclrhost.cpp" \
  "$native/pwrshplugin/pwrshplugin.def" plugin.res \
  -lwsmsvc -ladvapi32 -lole32 -luser32 "${static[@]}" -o pwrshplugin.dll
