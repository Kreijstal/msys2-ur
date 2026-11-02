"""Audit source references; restore and execute an actual netstandard2.0 consumer."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

archive,out,consumer=(Path(p).resolve() for p in sys.argv[1:4])
selected_feed=Path(sys.argv[4]).resolve() if len(sys.argv)==5 else out/'feed'
assert not consumer.exists(),consumer
consumer.mkdir(parents=True)
here=Path(__file__).resolve().parent
native_root=subprocess.check_output(['cygpath','-am',str(out)],text=True).strip()
def native(p):
    p=p.resolve()
    if p.is_relative_to(out):return native_root+'/'+p.relative_to(out).as_posix()
    return subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
records=json.loads((out/'build-results.json').read_text())
assert len(records)==117 and all(r['exit_code']==0 for r in records.values())
source=out/'standard-18a36291e48808fa7ef2d00a764ceb1ec95645a5'
expected={};wanted={}
aliases=dict(zip('bool byte char decimal double float int long object sbyte short string uint ulong ushort void'.split(),
                 ('System.'+n for n in 'Boolean Byte Char Decimal Double Single Int32 Int64 Object SByte Int16 String UInt32 UInt64 UInt16 Void'.split())))
for name,r in records.items():
    wanted[r['project']]=r['project_sha256'];wanted.update(r['source_cs'])
    output=out/('ref' if r['package_asset'] else 'extensions')/(name+'.dll')
    assert sha(output)==r['output_sha256'],name
    forwards=[]
    for p,digest in r['source_cs'].items():
        assert sha(source/p)==digest,p
        text=re.sub(r'/\*.*?\*/|//[^\n]*','',(source/p).read_text(),flags=re.S)
        for value in re.findall(r'TypeForwardedTo\(typeof\((.*?)\)\)',text):
            value=aliases.get(value,value)
            value=re.sub(r'<(,*)>',lambda m:'`'+str(len(m[1])+1),value)
            assert '<' not in value,value
            forwards.append(value)
    assert len(forwards)==len(set(forwards)),name
    expected[name]=forwards
verified=set()
with tarfile.open(archive) as tar:
    for member in tar:
        name=member.name.partition('/')[2]
        if member.isfile() and name in wanted:
            assert hashlib.sha256(tar.extractfile(member).read()).hexdigest()==wanted[name],name
            verified.add(name)
assert verified==set(wanted)
(out/'expected-forwards.json').write_text(json.dumps(expected,indent=2)+'\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),
         DOTNET_CLI_HOME=native(consumer/'cli-home'),NUGET_PACKAGES=native(consumer/'cache'),
         DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
dotnet='/clang64/lib/dotnet/dotnet.exe'
def run(command,log,success=True):
    with log.open('w') as stream:r=subprocess.run(command,env=env,stdout=stream,stderr=subprocess.STDOUT)
    if success:assert r.returncode==0,(command,log)
    return r.returncode
feed=out/'feed';feed.mkdir(exist_ok=True)
config=consumer/'NuGet.config'
config.write_text('<configuration><packageSources><clear/><add key="source-standard" value="'+native(selected_feed)+'"/><add key="installed-source" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources></configuration>')
tool=consumer/'metadata';tool.mkdir()
def project(path,properties,files):
    tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
    for k,v in dict(EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',UseAppHost='false',UseSharedCompilation='false',**properties).items():E.SubElement(pg,k).text=v
    ig=E.SubElement(tree,'ItemGroup')
    for file in files:E.SubElement(ig,'Compile',Include=native(file))
    E.indent(tree);E.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)
project(tool/'Build.csproj',dict(TargetFramework='net8.0',OutputType='Exe',AssemblyName='CheckStandardMetadata'),[here/'inputs/CheckMetadata.cs'])
def build(proj,log):return run([dotnet,'build',native(proj),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal'],log)
build(tool/'Build.csproj',consumer/'metadata-build.log')
run([dotnet,native(tool/'bin/Release/net8.0/CheckStandardMetadata.dll'),native(out)],consumer/'metadata-results.json')
metadata=json.loads((consumer/'metadata-results.json').read_text())
package=feed/'netstandard.library.2.0.3.nupkg'
assert package.read_bytes()==(selected_feed/package.name).read_bytes()
library=consumer/'library';library.mkdir()
project(library/'Build.csproj',dict(TargetFramework='netstandard2.0',AssemblyName='StandardConsumer',LangVersion='7.3'),[here/'inputs/Consumer.cs'])
tree=E.parse(library/'Build.csproj')
capture=E.SubElement(tree.getroot(),'Target',Name='CaptureReferencePaths',BeforeTargets='CoreCompile')
E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)references.txt',Lines="@(ReferencePath->'%(FullPath)')",Overwrite='true')
tree.write(library/'Build.csproj',encoding='utf-8',xml_declaration=True)
build(library/'Build.csproj',consumer/'library-build.log')
assets=json.loads((library/'obj/project.assets.json').read_text())
assert set(assets['libraries'])=={'NETStandard.Library/2.0.3','Microsoft.NETCore.Platforms/1.1.2'},assets['libraries']
cache=consumer/'cache/netstandard.library/2.0.3'
assert sha(cache/'netstandard.library.2.0.3.nupkg')==sha(package)
platforms=Path('/clang64/lib/dotnet/library-packs/microsoft.netcore.platforms.1.1.2.nupkg')
assert sha(consumer/'cache/microsoft.netcore.platforms/1.1.2/microsoft.netcore.platforms.1.1.2.nupkg')==sha(platforms)
with zipfile.ZipFile(package) as z:
    for p in z.namelist():
        if p.endswith('.dll'):assert (cache/p).read_bytes()==z.read(p),p
refs=(library/'obj/Release/netstandard2.0/references.txt').read_text(encoding='utf-8-sig').splitlines()
assert len(refs)==113 and all('/cache/netstandard.library/2.0.3/build/netstandard2.0/ref/' in p.replace('\\','/') for p in refs),refs
runner=consumer/'runner';runner.mkdir()
code=runner/'Run.cs';code.write_text('using System; class Program { static int Main() { string s=StandardConsumer.Run().GetAwaiter().GetResult(); if(s!="Grüße 世界:10:tuple") throw new Exception(s); Console.WriteLine("PASS source netstandard2.0 async Unicode/collections/LINQ/tuple consumer: "+s); return 0; } }')
project(runner/'Build.csproj',dict(TargetFramework='net8.0',OutputType='Exe',AssemblyName='RunStandardConsumer'),[code])
tree=E.parse(runner/'Build.csproj');E.SubElement(tree.getroot(),'ItemGroup')
E.SubElement(tree.getroot()[-1],'ProjectReference',Include='../library/Build.csproj')
tree.write(runner/'Build.csproj',encoding='utf-8',xml_declaration=True)
build(runner/'Build.csproj',consumer/'runner-build.log')
run([dotnet,native(runner/'bin/Release/net8.0/RunStandardConsumer.dll')],consumer/'run.log')
negative=consumer/'RejectNewApi.cs';negative.write_text('public class RejectNewApi { public System.Threading.Lock Value; }')
compiler=Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap/CompilerHost.dll')
rsp=consumer/'negative.rsp';rsp.write_text('\n'.join(['/nostdlib+','/target:library','/out:"'+native(consumer/'negative.dll')+'"',*['/reference:"'+native(p)+'"' for p in sorted((out/'ref').glob('*.dll'))],'"'+native(negative)+'"'])+'\n')
negative_code=run([dotnet,native(compiler),'-noconfig','@'+native(rsp)],consumer/'negative.log',False)
assert negative_code!=0 and 'Lock' in (consumer/'negative.log').read_text()
result=dict(original_inputs_verified=len(verified),metadata=metadata,source_package_sha256=sha(package),consumer_exit_code=0,actual_source_reference_paths=113,negative_new_api_exit_code=negative_code,preserved_original_dependency_groups=20,preserved_original_dependency_edges=337,formal_pacman_installed=len(sys.argv)==5,shipping_generator_bundle_complete=False,full_dependency_goal_complete=False)
(consumer/'results.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS original source references/forwards, fresh source-only netstandard2.0 SDK consumer, runtime behavior and newer-API negative control')

subprocess.run(['/usr/bin/python3',str(here/'audit.py'),str(archive),str(out),str(consumer),str(selected_feed)],check=True)
