#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
feed=$(cygpath -am "${2:-/clang64/lib/dotnet/library-packs}")
mkdir "${1:?usage: check.sh NEW_OUTPUT [FEED]}";out=$(cd "$1" && pwd)
export PATH=/clang64/bin:/usr/bin:$PATH
export DOTNET_ROOT=$(cygpath -m /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$out/cli-home") NUGET_PACKAGES=$(cygpath -m "$out/empty-packages")
cp "$here/"{MmiProbe.cs,MmiPortChecks.cs,MmiCredentialChecks.cs,MmiExtendedCallbackChecks.cs,MmiStreamChecks.cs,NativeDependencies.cs,Identity.cs} "$out/"
cat > "$out/NuGet.config" <<CONFIG
<configuration><packageSources><clear/><add key="source-built-port" value="$feed"/></packageSources></configuration>
CONFIG
/clang64/bin/clang -std=c11 -Wall -Wextra -Werror "$here/check-credential-abi.c" -lmi -o "$out/native-credential-abi.exe"
"$out/native-credential-abi.exe"
/clang64/bin/clang -std=c11 -shared -Wall -Wextra -Werror "$here/check-extended-callbacks.c" -o "$out/mmi-callback-driver.dll"
/clang64/bin/clang -std=c11 -shared -Wall -Wextra -Werror "$here/check-streamed-results.c" -o "$out/mmi-stream-driver.dll"
/usr/bin/python3 - "$here" "$out" <<'PY'
import hashlib,sys
from pathlib import Path
here,out=(Path(p) for p in sys.argv[1:])
key=bytes.fromhex((here/'MicrosoftShared.pubkey.hex').read_text())
assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='31bf3856ad364e35'
(out/'Friend.public.snk').write_bytes(key)
for suffix,assembly,cls in [('sma','System.Management.Automation','FriendSma'),('cim','Microsoft.Management.Infrastructure.CimCmdlets','FriendCimCmdlets')]:
 folder=out/('friend-'+suffix);folder.mkdir()
 (folder/'Friend.cs').write_text((here/'Friend.cs').read_text().replace('FRIEND_CLASS',cls))
 (folder/'Friend.csproj').write_text('''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><AssemblyName>'''+assembly+'''</AssemblyName><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><SignAssembly>true</SignAssembly><PublicSign>true</PublicSign><AssemblyOriginatorKeyFile>../Friend.public.snk</AssemblyOriginatorKeyFile><InformationalVersion>source-friend-access-check-only</InformationalVersion></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.Management.Infrastructure" Version="[3.0.0]"/></ItemGroup></Project>''')
PY
cat > "$out/Check.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><EnableDefaultCompileItems>false</EnableDefaultCompileItems></PropertyGroup><ItemGroup><Compile Include="*.cs"/><ProjectReference Include="friend-sma/Friend.csproj"/><ProjectReference Include="friend-cim/Friend.csproj"/><PackageReference Include="Microsoft.Management.Infrastructure" Version="[3.0.0]"/><None Include="mmi-callback-driver.dll" CopyToOutputDirectory="PreserveNewest"/><None Include="mmi-stream-driver.dll" CopyToOutputDirectory="PreserveNewest"/></ItemGroup></Project>
PROJECT
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -m "$out/Check.csproj")" -c Release --configfile "$(cygpath -m "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
for mode in local port capabilities;do
 args=();[[ $mode != port ]]||args=(--port-checks);[[ $mode != capabilities ]]||args=(--capabilities)
 timeout 90 /clang64/lib/dotnet/dotnet.exe "$(cygpath -m "$out/bin/Release/net8.0/Check.dll")" "${args[@]}"
done
