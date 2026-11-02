#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check.sh NEW_OUTPUT [NEW_FEED]}";out=$(cd "$1" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
cat > "$out/NuGet.config" <<XML
<configuration><packageSources><clear/>
XML
if [[ $# -ge 2 ]];then printf '<add key="new-source" value="%s"/>\n' "$(cygpath -am "$2")" >> "$out/NuGet.config";fi
printf '<add key="installed-source" value="%s"/></packageSources></configuration>\n' "$(cygpath -am /clang64/lib/dotnet/library-packs)" >> "$out/NuGet.config"
cp "$here/Check.cs" "$out/Program.cs"
cat > "$out/Check.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk">
<PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup>
<ItemGroup><Compile Include="Program.cs"/>
<PackageReference Include="Microsoft.CodeAnalysis.CSharp.Workspaces" Version="[4.9.2]"/>
<PackageReference Include="Microsoft.CodeAnalysis.VisualBasic.Workspaces" Version="[4.9.2]"/>
<PackageReference Include="Microsoft.CodeAnalysis.CSharp.CodeStyle" Version="[4.9.2]" GeneratePathProperty="true" ExcludeAssets="analyzers"/>
<PackageReference Include="Microsoft.CodeAnalysis.VisualBasic.CodeStyle" Version="[4.9.2]" GeneratePathProperty="true" ExcludeAssets="analyzers"/>
<Reference Include="Microsoft.CodeAnalysis.CodeStyle" HintPath="$(PkgMicrosoft_CodeAnalysis_CSharp_CodeStyle)/analyzers/dotnet/cs/Microsoft.CodeAnalysis.CodeStyle.dll"/>
<Reference Include="Microsoft.CodeAnalysis.CodeStyle.Fixes" HintPath="$(PkgMicrosoft_CodeAnalysis_CSharp_CodeStyle)/analyzers/dotnet/cs/Microsoft.CodeAnalysis.CodeStyle.Fixes.dll"/>
<Reference Include="Microsoft.CodeAnalysis.CSharp.CodeStyle" HintPath="$(PkgMicrosoft_CodeAnalysis_CSharp_CodeStyle)/analyzers/dotnet/cs/Microsoft.CodeAnalysis.CSharp.CodeStyle.dll"/>
<Reference Include="Microsoft.CodeAnalysis.CSharp.CodeStyle.Fixes" HintPath="$(PkgMicrosoft_CodeAnalysis_CSharp_CodeStyle)/analyzers/dotnet/cs/Microsoft.CodeAnalysis.CSharp.CodeStyle.Fixes.dll"/>
<Reference Include="Microsoft.CodeAnalysis.VisualBasic.CodeStyle" HintPath="$(PkgMicrosoft_CodeAnalysis_VisualBasic_CodeStyle)/analyzers/dotnet/vb/Microsoft.CodeAnalysis.VisualBasic.CodeStyle.dll"/>
<Reference Include="Microsoft.CodeAnalysis.VisualBasic.CodeStyle.Fixes" HintPath="$(PkgMicrosoft_CodeAnalysis_VisualBasic_CodeStyle)/analyzers/dotnet/vb/Microsoft.CodeAnalysis.VisualBasic.CodeStyle.Fixes.dll"/>
</ItemGroup></Project>
XML
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/Check.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -p:CscToolPath="$(cygpath -am /clang64/lib/dotnet/compiler-packs/roslyn-4.9.2)" -p:CscToolExe=csc49.cmd -v:minimal
payload=$out/empty-packages/microsoft.codeanalysis.csharp.codestyle/4.9.2/source-build
timeout 300 /clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$out/bin/Release/net8.0/Check.dll")" "$(cygpath -am "$here/ExpectedAssemblies.json")" "$(cygpath -am "$payload/localization.json")" "$(cygpath -am "$payload/UpstreamFixtures.json")" "$(cygpath -am /clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0)"
bash "$here/check-api.sh" "$out" "$out/api"
python3 "$here/verify-build-assets.py" "$here/ExpectedBuildAssets.json" "$out/empty-packages/microsoft.codeanalysis.csharp.codestyle/4.9.2/build" "$out/empty-packages/microsoft.codeanalysis.visualbasic.codestyle/4.9.2/build"
bash "$here/check-msbuild.sh" "$out" nuget
