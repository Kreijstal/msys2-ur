#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
prepared=$(cd "${1:?usage: check-prototype.sh PREPARED NEW_OUTPUT FIXTURES}" && pwd)
mkdir "${2:?missing new output}";out=$(cd "$2" && pwd)
fixtures=$(cygpath -am "${3:?missing fixture data}")
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
cp "$here/Check.cs" "$out/Program.cs"
cp "$here/CheckSpecialFixes.cs" "$out/"
mkdir "$out/payload"
for name in Microsoft.CodeAnalysis.Analyzers Microsoft.CodeAnalysis.CSharp.Analyzers Microsoft.CodeAnalysis.VisualBasic.Analyzers;do
 cp "$prepared/$name/bin/Release/net8.0/$name.dll" "$out/payload/"
done
for culture in cs de es fr it ja ko pl pt-BR ru tr zh-Hans zh-Hant;do
 mkdir "$out/payload/$culture"
 cp "$prepared/Microsoft.CodeAnalysis.Analyzers/bin/Release/net8.0/$culture/Microsoft.CodeAnalysis.Analyzers.resources.dll" "$out/payload/$culture/"
done
cat > "$out/Check.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.CodeAnalysis.CSharp.Workspaces" Version="[4.9.2]"/><PackageReference Include="Microsoft.CodeAnalysis.VisualBasic.Workspaces" Version="[4.9.2]"/><None Include="payload/**/*.dll" Link="%(RecursiveDir)%(Filename)%(Extension)" CopyToOutputDirectory="PreserveNewest"/></ItemGroup></Project>
PROJECT
cp "$prepared/NuGet.config" "$out/"
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/Check.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
timeout 240 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/bin/Release/net8.0/Check.dll")" "$(cygpath -am "$here/ExpectedInventory.json")" "$(cygpath -am "$prepared/localization.json")" "$fixtures" "$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0)" "$(cygpath -am "$out/fixture-results.json")"
