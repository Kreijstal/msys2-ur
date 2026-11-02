#!/usr/bin/env bash
set -euo pipefail
out=$(cd "${1:?missing prepared}" && pwd)
here=$(cd "$(dirname "$0")" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/evaluation-tool/Build.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal > "$out/evaluation-build.log" 2>&1
export MSBuildSDKsPath=$(cygpath -am /clang64/lib/dotnet/sdk/8.0.131/Sdks) MSBUILD_EXE_PATH=$(cygpath -am /clang64/lib/dotnet/sdk/8.0.131/MSBuild.dll)
for plan in plan plan-generic plan-asn1;do
 /clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$out/evaluation-tool/bin/Release/net8.0/Build.dll")" "$(cygpath -am "$out/$plan/wrappers.json")" "$(cygpath -am "$out/$plan/evaluated.json")" > "$out/$plan/evaluate.log" 2>&1
done
/clang64/bin/python.exe -X utf8 "$(cygpath -am "$here/generate-asn.py")" "$(cygpath -am "$out")" > "$out/generate-asn.log" 2>&1
bash "$here/interop/build.sh" "$out/interop" > "$out/interop-build.log" 2>&1
/clang64/bin/python.exe -X utf8 "$(cygpath -am "$here/interop/audit.py")" "$(cygpath -am "$out/interop")"
refs=$(cygpath -am /clang64/lib/dotnet/reference-packs/runtime-9.0.11/ref/net9.0)
/clang64/bin/python.exe -X utf8 "$(cygpath -am "$here/asn1/build-library.py")" "$(cygpath -am "$out/plan-asn1")" "$refs" "$(cygpath -am "$out/asn1-release")" > "$out/asn1-compile.log" 2>&1
for pair in plan:windows-release plan-generic:generic-release;do
 plan=${pair%:*};target=${pair#*:}
 /clang64/bin/python.exe -X utf8 "$(cygpath -am "$here/build-library.py")" "$(cygpath -am "$out/$plan")" "$refs" "$(cygpath -am "$out/$target")" "$(cygpath -am "$out/interop/Microsoft.Interop.LibraryImportGenerator/bin/Release/net8.0")" "$(cygpath -am "$out/asn1-release/System.Formats.Asn1.dll")" > "$out/$target.log" 2>&1
done
/clang64/bin/python.exe -X utf8 "$(cygpath -am "$here/pack.py")" "$(cygpath -am "$out")"
