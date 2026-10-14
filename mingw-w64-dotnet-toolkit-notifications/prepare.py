from pathlib import Path
import hashlib
import json
import sys
root=Path(sys.argv[1])
removed=[]
for p in sorted(root.rglob('*')):
    if p.is_file() and p.suffix.lower() in {'.exe','.dll','.winmd','.nupkg','.pdb','.obj','.lib'}:
        removed.append({'path':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()});p.unlink()
(root/'removed-binaries.json').write_text(json.dumps(removed,indent=2)+'\n')
# Use the desktop implementation, including native toast activation, against the
# source-built modern projection. SDK.Extras and old Framework packages are not used.
for p in list(root.rglob('Directory.Build.*'))+[root/'global.json',root/'Directory.Packages.props']:
    if p.is_file():p.unlink()
p=root/'Microsoft.Toolkit.Uwp.Notifications/Microsoft.Toolkit.Uwp.Notifications.csproj'
p.write_text('''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0-windows</TargetFramework><UseWindowsForms>true</UseWindowsForms><DefineConstants>$(DefineConstants);NETFX_CORE;WINDOWS_UWP;WIN32</DefineConstants><Version>7.1.3</Version><PackageId>Microsoft.Toolkit.Uwp.Notifications</PackageId><PackageLicenseExpression>MIT</PackageLicenseExpression><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Msys2.Windows.WinRT" Version="[0.1.1]"/></ItemGroup></Project>''')
