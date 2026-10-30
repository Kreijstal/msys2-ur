#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check.sh NEW_OUTPUT [NEW_FEED]}";out=$(cd "$1" && pwd)
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
/usr/bin/python3 "$here/prepare-check.py" "$here" "$out" "${@:2}"
flags=(-c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -p:CscToolPath=$(cygpath -m "$MINGW_PREFIX")/lib/dotnet/compiler-packs/roslyn-4.9.2 -p:CscToolExe=csc49.cmd -v:minimal)
build() { ${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$1/Check.csproj")" "${flags[@]}"; }
run() { ${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$1/bin/Release/net8.0/Check.dll")" "${@:2}"; }
build "$out"
/usr/bin/python3 "$here/verify-consumer.py" "$out"
hash=$(cat "$out/source-runtime-sha256.txt")
run "$out" runtime "$hash"
for name in Gen3.11 Gen4.0 Gen4.4;do
 run "$out" generator "$hash" "$(cygpath -am "$out/copies/$name/bin/Release/net8.0/System.Text.Json.SourceGeneration.dll")" $(cygpath -m "$MINGW_PREFIX")/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0
done
build "$out/sample";run "$out/sample"
/usr/bin/python3 "$here/verify-sdk.py" "$out"
for tool in tools pe;do build "$out/$tool";done
mkdir "$out/api";assemblies=()
for name in Lib Gen3.11 Gen4.0 Gen4.4;do
 if [[ $name == Lib ]];then filename=System.Text.Json;else filename=System.Text.Json.SourceGeneration;fi
 path="$out/copies/$name/bin/Release/net8.0/$filename.dll"
 run "$out/tools" $(cygpath -m "$MINGW_PREFIX")/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0 "$(cygpath -am "$path")" $(cygpath -m "$MINGW_PREFIX")/lib/dotnet/compiler-packs/roslyn-4.9.2 > "$out/api/$name.json"
 assemblies+=("$(cygpath -am "$path")")
 if [[ $name != Lib ]];then for path in "$out/copies/$name/bin/Release/net8.0"/*/System.Text.Json.SourceGeneration.resources.dll;do assemblies+=("$(cygpath -am "$path")");done;fi
done
run "$out/pe" "${assemblies[@]}" > "$out/metadata.json"
/usr/bin/python3 "$here/compare.py" "$here" "$out"
echo 'PASS fresh source JSON consumer, all generator variants/SDK discovery, exact API/resource/linker/payload gates'
