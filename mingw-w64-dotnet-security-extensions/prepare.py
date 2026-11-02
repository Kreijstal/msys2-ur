from pathlib import Path
import sys,hashlib,shutil
source,out=(Path(x).resolve() for x in sys.argv[1:]);out.mkdir()
key=bytes.fromhex((source/'MicrosoftShared.pubkey.hex').read_text())
assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='31bf3856ad364e35'
(out/'Library.public.snk').write_bytes(key)
for file in ['FileSignatureInfo.cs','README.md']:
    shutil.copyfile(source/file,out/file)
(out/'Library.csproj').write_text('''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><AssemblyName>getfilesiginforedistwrapper</AssemblyName><PackageId>Microsoft.Security.Extensions</PackageId><Version>1.4.0</Version><AssemblyVersion>10.0.0.0</AssemblyVersion><FileVersion>1.4.0.0</FileVersion><InformationalVersion>1.4.0-msys2-source-port+wintrust</InformationalVersion><IncludeSourceRevisionInInformationalVersion>false</IncludeSourceRevisionInInformationalVersion><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><EnableDefaultItems>false</EnableDefaultItems><SignAssembly>true</SignAssembly><PublicSign>true</PublicSign><AssemblyOriginatorKeyFile>Library.public.snk</AssemblyOriginatorKeyFile><PackageLicenseExpression>MIT</PackageLicenseExpression><PackageReadmeFile>README.md</PackageReadmeFile><Description>Windows WinTrust source replacement for the Microsoft.Security.Extensions 1.4 contract.</Description></PropertyGroup><ItemGroup><Compile Include="FileSignatureInfo.cs"/><None Include="README.md" Pack="true" PackagePath="/"/><None Include="msys-file-signature.dll" Pack="true" PackagePath="runtimes/win-x64/native/"/></ItemGroup></Project>''')
(out/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
