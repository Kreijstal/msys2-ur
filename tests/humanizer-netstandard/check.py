"""Fresh netstandard2.0 source Humanizer consumer, full resources/API and archive audit."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import struct
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

resume='--resume' in sys.argv[1:]
root,out,check=(Path(p).resolve() for p in sys.argv[1:] if p!='--resume')
assert resume or not check.exists(),check
check.mkdir(parents=True,exist_ok=resume)
here=Path(__file__).resolve().parent
record=json.loads((out/'source-inputs.json').read_text())
source=out/('Humanizer-'+record['source_commit']);main=source/'src/Humanizer'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
native_root=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
def native(p):
    p=p.resolve()
    if p.is_relative_to(root):return native_root+'/'+p.relative_to(root).as_posix()
    return subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
def posix(p):
    p=p.replace('\\','/').rstrip('/');assert p.lower().startswith(native_root.lower()+'/'),p
    return root/p[len(native_root)+1:]
def save(tree,path):
    E.indent(tree);E.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)
def config(path,feeds):
    tree=E.Element('configuration');items=E.SubElement(tree,'packageSources');E.SubElement(items,'clear')
    for i,feed in enumerate(feeds):E.SubElement(items,'add',key='source'+str(i),value=native(feed))
    save(tree,path)
platforms=check/'platform-feed';platforms.mkdir(exist_ok=resume)
platform_source=Path('/clang64/lib/dotnet/library-packs/microsoft.netcore.platforms.1.1.2.nupkg')
shutil.copyfile(platform_source,platforms/platform_source.name)
library_feeds=[out/'feed',root/'netstandard20-2/feed',platforms]
tool_feeds=[root/'roslyn414-1/feed',root/'roslyn-deps9-1/feed',Path('/clang64/lib/dotnet/library-packs')]
config(check/'NuGet.config',library_feeds);config(check/'Tools.NuGet.config',tool_feeds)
def project(path,props,files,packages):
    tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
    for k,v in dict(EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',UseSharedCompilation='false',UseAppHost='false',LangVersion='preview',**props).items():E.SubElement(pg,k).text=v
    items=E.SubElement(tree,'ItemGroup')
    for file in files:E.SubElement(items,'Compile',Include=native(file))
    for name,version in packages.items():E.SubElement(items,'PackageReference',Include=name,Version='['+version+']')
    save(tree,path)
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(check/'cli-home'),NUGET_PACKAGES=native(check/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
dotnet='/clang64/lib/dotnet/dotnet.exe'
def run(command,log,extra=None):
    with log.open('w') as stream:r=subprocess.run(command,env=dict(env,**(extra or {})),stdout=stream,stderr=subprocess.STDOUT)
    assert r.returncode==0,(command,log)
library=check/'library';library.mkdir(exist_ok=resume)
project(library/'Build.csproj',dict(TargetFramework='netstandard2.0',AssemblyName='StandardHumanizerConsumer'),[here/'inputs/Consumer.cs'],{'Humanizer.Core':'2.14.1'})
run([dotnet,'build',native(library/'Build.csproj'),'-c','Release','--configfile',native(check/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],check/'library-build.log')
resources=[]
for p in sorted((main/'Properties').glob('Resources*.resx')):
    culture=p.stem.removeprefix('Resources').removeprefix('.')
    resources.append(dict(culture=culture,strings={e.get('name'):e.findtext('value') or '' for e in E.parse(p).iter('data')}))
compile_paths=[posix(p) for p in (main/'obj/Release/netstandard2.0/Compile.txt').read_text(encoding='utf-8-sig').splitlines() if p]
original_cs=[p for p in compile_paths if p.is_relative_to(main) and not p.is_relative_to(main/'obj')]
assert set(p.relative_to(source).as_posix() for p in original_cs)=={p for p in record['original_inputs'] if p.endswith('.cs')}
refs=[posix(p) for p in (main/'obj/Release/netstandard2.0/ReferencePath.txt').read_text(encoding='utf-8-sig').splitlines() if p]
runner=check/'runner';runner.mkdir(exist_ok=resume)
project(runner/'Build.csproj',dict(TargetFramework='net8.0',OutputType='Exe',AssemblyName='CheckHumanizerNetstandard',Nullable='enable'),[here/'inputs/Check.cs',here/'inputs/CheckApi.cs'],{'Microsoft.CodeAnalysis.CSharp':'4.14.0'})
run([dotnet,'build',native(runner/'Build.csproj'),'-c','Release','--configfile',native(check/'Tools.NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],check/'runner-build.log',dict(NUGET_PACKAGES=native(check/'tool-cache')))
# Derive only the public portion from the original repository signing key.
key=(main/'Humanizer.snk').read_bytes()
assert key[:4]==bytes([7,2,0,0]) and struct.unpack_from('<I',key,8)[0]==0x32415352
bits,exponent=struct.unpack_from('<II',key,12);public_size=20+bits//8
public=struct.pack('<III',0x2400,0x8004,public_size)+bytes([6,2,0,0])+key[4:8]+struct.pack('<III',0x31415352,bits,exponent)+key[20:20+bits//8]
token=hashlib.sha1(public).digest()[-8:][::-1].hex()
settings=dict(build_output=native(main/'bin/Release/netstandard2.0'),consumer_output=native(library/'bin/Release/netstandard2.0'),expected_public_key_token=token,expected_public_key_hex=public.hex(),resources=resources,original_source_paths=[native(p) for p in original_cs],reference_paths=[native(p) for p in refs],defines=['NETSTANDARD','NETSTANDARD2_0','NETSTANDARD2_0_OR_GREATER'])
(check/'settings.json').write_text(json.dumps(settings,ensure_ascii=False,indent=2)+'\n')
run([dotnet,native(runner/'bin/Release/net8.0/CheckHumanizerNetstandard.dll'),native(check/'settings.json'),native(check/'runtime-results.json')],check/'run.log')
archive=root/'humanizer-3ebc38de.tar.gz';assert sha(archive)==record['archive_sha256']
verified=set()
with tarfile.open(archive) as tar:
    assert tar.pax_headers['comment']==record['source_commit']
    for member in tar:
        name=member.name.partition('/')[2]
        if member.isfile() and name in record['original_inputs']:
            assert hashlib.sha256(tar.extractfile(member).read()).hexdigest()==record['original_inputs'][name],name
            assert sha(source/name)==record['original_inputs'][name],name;verified.add(name)
assert verified==set(record['original_inputs'])
package=out/'feed/Humanizer.Core.2.14.1.nupkg'
with zipfile.ZipFile(package) as z:
    for path in z.namelist():
        if path.startswith('lib/netstandard2.0/') and path.endswith('.dll'):
            assert (main/'bin/Release/netstandard2.0'/path.removeprefix('lib/netstandard2.0/')).read_bytes()==z.read(path),path
    for relative,name in [('LICENSE','LICENSE'),('src/Humanizer/Bytes/LICENSE','LICENSE.Bytes'),('src/Humanizer/Inflections/LICENSE','LICENSE.Inflections')]:assert z.read(name)==(source/relative).read_bytes()
    spec=E.fromstring(z.read(next(p for p in z.namelist() if p.endswith('.nuspec'))));md=next(e for e in spec if e.tag.endswith('metadata'))
    assert all(e.get('targetFramework')=='.NETStandard2.0' for e in md.iter() if e.tag.endswith('group'))
    repo=next(e for e in md if e.tag.endswith('repository'));assert repo.get('commit')==record['source_commit']
audits=[]
for file,feeds in [(main/'obj/project.assets.json',[root/'netstandard20-2/feed',Path('/clang64/lib/dotnet/library-packs')]),(library/'obj/project.assets.json',library_feeds),(runner/'obj/project.assets.json',tool_feeds)]:
    available={}
    for feed in feeds:
        for p in feed.glob('*.nupkg'):available.setdefault(p.name.lower(),p)
    assets=json.loads(file.read_text());folders=list(assets['packageFolders']);assert len(folders)==1;cache=posix(folders[0])
    for name,entry in assets['libraries'].items():
        if entry['type']!='package':continue
        ident,version=name.split('/');filename=ident.lower()+'.'+version+'.nupkg';assert filename in available,name
        expected=available[filename];assert sha(cache/entry['path']/filename)==sha(expected),(name,file)
        with zipfile.ZipFile(expected) as z:
            for path in z.namelist():
                if path.endswith('.dll'):assert (cache/entry['path']/path).read_bytes()==z.read(path),(name,path)
        audits.append(dict(assets=str(file.relative_to(root)),package=name,sha256=sha(expected)))
result=dict(original_source_project_resource_key_license_inputs_verified=len(verified),actual_original_compiled_cs_files=len(original_cs),source_package_sha256=sha(package),runtime=json.loads((check/'runtime-results.json').read_text()),actual_source_compile_and_consumer_package_references_verified=len(audits),package_audits=audits,original_project_and_cs_changes=0,all_package_license_and_resource_bytes_match_originals=True,all_actual_cache_archives_and_dlls_match_source=True,formal_pacman_installed=False,full_dependency_goal_complete=False)
(check/'results.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS original Humanizer netstandard2.0 sources/project, full resource/API/runtime checks, source-only consumers/caches and three licenses')
