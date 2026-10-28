# SPDX-License-Identifier: MIT
# Native apphosts need the real runtime root, behind the bin/dotnet launcher.
if [ -n "${MINGW_PREFIX:-}" ] && [ -f "${MINGW_PREFIX}/lib/dotnet/dotnet.exe" ]; then
  export DOTNET_ROOT="${DOTNET_ROOT:-$(cygpath -w "${MINGW_PREFIX}/lib/dotnet")}"
  export DOTNET_ROOT_X64="${DOTNET_ROOT_X64:-${DOTNET_ROOT}}"
fi
