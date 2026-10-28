"""Stage the pinned core telemetry source without networked build tooling."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E

source,output=(Path(x).resolve() for x in sys.argv[1:]);output.mkdir()
inputs=Path(__file__).resolve().parent
removed=[]
for path in sorted(source.rglob('*')):
    if path.is_file() and path.suffix.lower() in {'.dll','.exe','.nupkg','.pdb','.snk','.obj','.lib','.a','.resources'}:
        removed.append(str(path.relative_to(source)));path.unlink()
(output/'removed-binaries.json').write_text(json.dumps(removed,indent=2)+'\n')
core=source/'BASE/src/Microsoft.ApplicationInsights'
version=E.parse(source/'.props/_GlobalStaticVersion.props')
ns={'m':'http://schemas.microsoft.com/developer/msbuild/2003'}
assert [version.findtext('.//m:SemanticVersion'+part,namespaces=ns) for part in ['Major','Minor','Patch']]==['2','23','0']
key=bytes.fromhex((inputs/'MicrosoftShared.pubkey.hex').read_text())
assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='31bf3856ad364e35'
assert key.hex() in (core/'Properties/AssemblyInfo.cs').read_text(encoding='utf-8-sig')
(output/'MicrosoftShared.public.snk').write_bytes(key)
project=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(project,'PropertyGroup')
values=dict(TargetFramework='net8.0',AssemblyName='Microsoft.ApplicationInsights',RootNamespace='Microsoft.ApplicationInsights',
    Version='2.23.0',AssemblyVersion='2.23.0.29',FileVersion='2.23.0.29',
    InformationalVersion='2.23.0+2faa7e8b157a431daa2e71785d68abd5fa817b53',IncludeSourceRevisionInInformationalVersion='false',
    EnableDefaultItems='false',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',
    EnableNETAnalyzers='false',NuGetAudit='false',Nullable='disable',SignAssembly='true',PublicSign='true',
    AssemblyOriginatorKeyFile='MicrosoftShared.public.snk',DefineConstants='$(DefineConstants);NETSTANDARD;NETSTANDARD2_0;PUBLIC_RELEASE',
    PackageLicenseExpression='MIT',RepositoryUrl='https://github.com/microsoft/ApplicationInsights-dotnet',RepositoryType='git',
    RepositoryCommit='2faa7e8b157a431daa2e71785d68abd5fa817b53',NoWarn='CS0618;SYSLIB0051;SYSLIB0003;CS0672')
for name,value in values.items():E.SubElement(props,name).text=value
items=E.SubElement(project,'ItemGroup')
for path in sorted(core.rglob('*.cs')):
    E.SubElement(items,'Compile',Include=os.path.relpath(path,output).replace('\\','/'))
E.SubElement(items,'PackageReference',Include='System.Diagnostics.DiagnosticSource',Version='[8.0.1]')
E.indent(project);E.ElementTree(project).write(output/'Library.csproj',encoding='utf-8',xml_declaration=True)
baseline=source/'.publicApi/Microsoft.ApplicationInsights.dll/netstandard2.0'
(output/'PublicAPI.txt').write_text((baseline/'PublicAPI.Shipped.txt').read_text()+'\n'+(baseline/'PublicAPI.Unshipped.txt').read_text())
feed=os.environ.get('APPINSIGHTS_SOURCE_FEED',os.environ.get('MINGW_PREFIX','/clang64')+'/lib/dotnet/library-packs')
if sys.platform.startswith(('cygwin','msys')):feed=subprocess.check_output(['cygpath','-am',feed],text=True).strip()
(output/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="installed-source-built" value="'+feed+'"/></packageSources></configuration>\n')
