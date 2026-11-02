#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
prepared=$(cd "${1:?usage: check-prototype.sh PREPARED NEW_OUTPUT SOURCE}" && pwd)
source=$(cd "${3:?missing source}" && pwd)
mkdir "${2:?missing new output}";out=$(cd "$2" && pwd)
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet)
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
cp "$here/CheckPrototype.cs" "$out/Program.cs"
cp "$here/CheckGenerated.cs" "$out/"
cat > "$out/Check.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.CodeAnalysis.CSharp.Workspaces" Version="[4.9.2]"/></ItemGroup></Project>
PROJECT
cp "$prepared/NuGet.config" "$out/"
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/Check.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
for name in StyleCop.Analyzers StyleCop.Analyzers.CodeFixes;do
 cp "$prepared/$name/bin/Release/net8.0/$name.dll" "$out/bin/Release/net8.0/"
done
for culture in de-DE en-GB es-MX fr-FR pl-PL pt-BR ru-RU;do
 mkdir -p "$out/bin/Release/net8.0/$culture"
 cp "$prepared/StyleCop.Analyzers/bin/Release/net8.0/$culture/StyleCop.Analyzers.resources.dll" "$out/bin/Release/net8.0/$culture/"
done
${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/bin/Release/net8.0/Check.dll")" "$(cygpath -am "$here/ExpectedInventory.json")" "$(cygpath -am "$prepared/localization.json")" "$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0)" "$(cygpath -am "$source")" "$(cygpath -am "$prepared")"
mkdir "$out/msbuild"
cat > "$out/msbuild/Sample.csproj" <<PROJECT
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><WarningsAsErrors>SA1001</WarningsAsErrors></PropertyGroup><ItemGroup><Analyzer Include="$(cygpath -am "$prepared/StyleCop.Analyzers/bin/Release/net8.0/StyleCop.Analyzers.dll")"/></ItemGroup></Project>
PROJECT
printf 'class C { int[] x = { 1,2 }; }\n' > "$out/msbuild/Sample.cs"
build_sample() {
 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/msbuild/Sample.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -p:CscToolPath="$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/compiler-packs/roslyn-4.9.2)" -p:CscToolExe=csc49.cmd -v:minimal
}
if build_sample > "$out/msbuild/expected-error.log" 2>&1;then
 echo 'FAIL: MSBuild accepted the deliberately invalid comma spacing' >&2;exit 1
fi
grep -E 'error SA1001:' "$out/msbuild/expected-error.log"
if grep -E 'AD0001|CS8032|CS9057' "$out/msbuild/expected-error.log";then exit 1;fi
printf 'class C { int[] x = { 1, 2 }; }\n' > "$out/msbuild/Sample.cs"
build_sample > "$out/msbuild/corrected.log" 2>&1
echo 'PASS real MSBuild/source-csc49 analyzer loading, expected SA1001 error and corrected build'
