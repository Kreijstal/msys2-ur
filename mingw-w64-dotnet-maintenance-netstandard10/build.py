"""Build original Unsafe IL and four C# maintenance packages for netstandard2.0."""
from pathlib import Path
import json
import os
import struct
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

root,out=(Path(p).resolve() for p in sys.argv[1:])
here=Path(__file__).resolve().parent
manifest=json.loads((out/'source-inputs.json').read_text())
import hashlib
for record in manifest['projects'].values():
    source=out/('maintenance-packages-'+record['commit'])
    for path,digest in record['original_sources'].items():
        assert hashlib.sha256((source/path).read_bytes()).hexdigest()==digest,path
native_root=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
def native(p):
    p=p.resolve()
    if p.is_relative_to(root):return native_root+'/'+p.relative_to(root).as_posix()
    return subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
cache=Path(os.environ.get('MAINTENANCE_BOOTSTRAP_CACHE',str(out/'cache')))
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),
         DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(cache),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
dotnet='/clang64/lib/dotnet/dotnet.exe'
def run(command,log,cwd=None):
    with log.open('w') as stream:r=subprocess.run(command,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT)
    assert r.returncode==0,(command,log)
name='System.Runtime.CompilerServices.Unsafe';record=manifest['projects'][name]
source=out/('maintenance-packages-'+record['commit']);folder=out/name
version=folder/'versioning';version.mkdir(exist_ok=True)
tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
for k,v in dict(TargetFramework='netstandard2.0',AssemblyName=name,Version=record['version'],AssemblyVersion=record['version']+'.0',FileVersion=record['version']+'.0',InformationalVersion=record['version']+'+'+record['commit'],IncludeSourceRevisionInInformationalVersion='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',UseSharedCompilation='false',Company='Microsoft Corporation',Product='Microsoft® .NET',Description=name,GenerateAssemblyConfigurationAttribute='false').items():E.SubElement(pg,k).text=v
E.indent(tree);E.ElementTree(tree).write(version/'Build.csproj',encoding='utf-8',xml_declaration=True)
run([dotnet,'build',native(version/'Build.csproj'),'-c','Release','--configfile',native(out/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],folder/'versioning-build.log')
# Preserve the C# compiler's complete native VERSIONINFO payload in the IL image.
# ILAsm requires a two-section resource COFF object, which llvm-cvtres produces.
pe=(version/'bin/Release/netstandard2.0'/(name+'.dll')).read_bytes()
u16=lambda o:struct.unpack_from('<H',pe,o)[0]
u32=lambda o:struct.unpack_from('<I',pe,o)[0]
coff=u32(0x3c)+4;optional=coff+20
resource_rva=u32(optional+(112 if u16(optional)==0x20b else 96)+16)
sections=optional+u16(coff+16)
def file_offset(rva):
    for i in range(u16(coff+2)):
        s=sections+i*40;virtual,size,raw=u32(s+12),u32(s+16),u32(s+20)
        if virtual<=rva<virtual+max(size,u32(s+8)):return raw+rva-virtual
    raise AssertionError(rva)
base=file_offset(resource_rva)
def entries(relative):
    start=base+relative
    return [(u32(start+16+i*8),u32(start+20+i*8)) for i in range(u16(start+12)+u16(start+14))]
node=next(v for k,v in entries(0) if k==16)
assert node&0x80000000
types=entries(node&0x7fffffff);assert len(types)==1 and types[0][0]==1
languages=entries(types[0][1]&0x7fffffff);assert len(languages)==1
data=base+languages[0][1]
blob=pe[file_offset(u32(data)):file_offset(u32(data))+u32(data+4)]
(folder/'native-version.bin').write_bytes(blob)
(folder/'native-version.rc').write_text('1 16 "native-version.bin"\n')
run(['/clang64/bin/llvm-rc.exe','-fo','native-version.res','native-version.rc'],folder/'version-rc.log',folder)
run(['/clang64/bin/llvm-cvtres.exe','-machine:x86','-out:native-version.obj','native-version.res'],folder/'version-cvtres.log',folder)
include=folder/'include';include.mkdir(exist_ok=True)
(include/'version.h').write_text('#define CORE_ASSEMBLY "netstandard"\n#define ASSEMBLY_VERSION "6:0:0:0"\n#define CORE_ASSEMBLY_VERSION "2:0:0:0"\n#define FILE_VERSION "{string(\''+record['version']+'.0\')}"\n#define INFORMATIONAL_VERSION "{string(\''+record['version']+'+'+record['commit']+'\')}"\n.assembly extern CORE_ASSEMBLY { .publickeytoken = (CC 7B 13 FF CD 2D DD 51) .ver CORE_ASSEMBLY_VERSION }\n')
binary=folder/(name+'.dll')
il=source/next(iter(record['original_sources']))
run([native(Path('/clang64/bin/ilasm10.exe')),'-DLL','-DEBUG=OPT','-DET','-INCLUDE='+native(include),'-KEY='+native(out/'Microsoft.pubkey'),'-RESOURCE='+native(folder/'native-version.obj'),'-OUTPUT='+native(binary),native(il)],folder/'ilasm-build.log')
spec=E.parse(here/'inputs'/(name+'.publisher.nuspec'));ns={'m':'http://schemas.microsoft.com/packaging/2012/06/nuspec.xsd'}
E.register_namespace('',ns['m'])
metadata=spec.find('m:metadata',ns)
for e in list(metadata):
    tag=e.tag.rsplit('}',1)[-1]
    if tag in {'icon','frameworkAssemblies'}:metadata.remove(e)
    if tag=='dependencies':
        for group in list(e):
            if group.get('targetFramework')!='.NETStandard2.0':e.remove(group)
package=out/'feed'/(name+'.'+record['version']+'.nupkg')
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
    z.writestr(name+'.nuspec',E.tostring(spec.getroot(),encoding='utf-8',xml_declaration=True))
    z.write(binary,'lib/netstandard2.0/'+binary.name)
    pdb=binary.with_suffix('.pdb')
    if pdb.is_file():z.write(pdb,'lib/netstandard2.0/'+pdb.name)
    for file in ['LICENSE','LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:
        if (source/file).is_file():z.write(source/file,file)
    for file in ['PACKAGE.md',name+'.xml']:z.write(il.parent/file,file if file.endswith('.md') else 'lib/netstandard2.0/'+file)
run(['/usr/bin/python3',str(here/'pack.py'),str(out),name],folder/'package-metadata.log')
print('PASS unchanged original IL source package',name,flush=True)
for name in manifest['order'][1:]:
    # Refresh this private packaging input for already prepared outputs too.
    project=out/name/'Build.csproj';tree=E.parse(project)
    license=out/('maintenance-packages-'+manifest['projects'][name]['commit'])/'LICENSE'
    if not any(e.get('Include')==native(license) for e in tree.iter('None')):
        E.SubElement(E.SubElement(tree.getroot(),'ItemGroup'),'None',Include=native(license),Pack='true',PackagePath='')
        E.indent(tree);tree.write(project,encoding='utf-8',xml_declaration=True)
    run([dotnet,'pack',native(out/name/'Build.csproj'),'-c','Release','--configfile',native(out/'NuGet.config'),'-o',native(out/'feed'),'-p:UseSharedCompilation=false','-v:minimal'],out/name/'build.log')
    run(['/usr/bin/python3',str(here/'pack.py'),str(out),name],out/name/'package-metadata.log')
    print('PASS original netstandard2.0 C# package',name,flush=True)
print('PASS all five original-source maintenance packages',flush=True)
