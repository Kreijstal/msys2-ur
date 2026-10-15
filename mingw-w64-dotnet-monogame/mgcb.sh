#!/usr/bin/env bash
# MonoGame Content Builder, framework-dependent build running on the MSYS2 .NET runtime.
# Arguments are /option:value switches; MSYS must not rewrite them as paths,
# so pass file paths in Windows or relative form.
_prefix=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export MSYS2_ARG_CONV_EXCL='*'
exec "$_prefix/lib/dotnet/dotnet.exe" "$(cygpath -m "$_prefix/lib/monogame/mgcb/mgcb.dll")" "$@"
