"""Audit the complete original source Standard2.1 references and execute a fresh SDK consumer."""
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
selected_pack=Path(sys.argv[4]).resolve() if len(sys.argv)==5 else out/'pack'
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
assert len(records)==125 and all(r['exit_code']==0 for r in records.values())
source=out/'standard-a5b5f2e1e369972c8ff1e2183979fab6099f52ef'
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
for policy in ['Directory.Build.props','Directory.Build.targets','eng/Versions.props','eng/versioning.targets',
               'eng/ReferenceAssemblies.props','eng/Version.Details.xml','src/netstandard/ref/Directory.Build.props',
               'src/netstandard/pkg/shims/Directory.Build.targets','src/netstandard/pkg/shims/netstandard/Directory.Build.props',
               'src/netstandard/pkg/shims/netfx/Directory.Build.props','src/platforms/extensions/Directory.Build.props']:
    wanted[policy]=sha(source/policy)
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
config=consumer/'NuGet.config'
config.write_text('<configuration><packageSources><clear/></packageSources></configuration>')
def run(command,log,success=True):
    with log.open('w') as stream:r=subprocess.run(command,env=env,stdout=stream,stderr=subprocess.STDOUT)
    if success:assert r.returncode==0,(command,log)
    return r.returncode
def project(path,properties,files):
    tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
    for k,v in dict(EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',UseAppHost='false',UseSharedCompilation='false',**properties).items():E.SubElement(pg,k).text=v
    ig=E.SubElement(tree,'ItemGroup')
    for file in files:E.SubElement(ig,'Compile',Include=native(file))
    E.indent(tree);E.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)
def build(proj,log):return run([dotnet,'build',native(proj),'-c','Release','--configfile',native(config),'-v:minimal'],log)
tool=consumer/'metadata';tool.mkdir()
project(tool/'Build.csproj',dict(TargetFramework='net8.0',OutputType='Exe',AssemblyName='CheckStandardMetadata'),[here/'inputs/CheckMetadata.cs'])
build(tool/'Build.csproj',consumer/'metadata-build.log')
run([dotnet,native(tool/'bin/Release/net8.0/CheckStandardMetadata.dll'),native(out)],consumer/'metadata-results.json')
metadata=json.loads((consumer/'metadata-results.json').read_text())
assert metadata['assemblies']==125 and metadata['reference_assemblies_runtime_rejected']==121

# Execute the pinned original Arcade version task, including its original three test vectors.
version=consumer/'version';version.mkdir()
program=version/'Program.cs'
seed=json.loads((out/'tool-inputs.json').read_text())['source_date'][:10].replace('-','')+'.1'
program.write_text('''using System;using Microsoft.DotNet.Arcade.Sdk;
class Program {static int Main(string[] args) {
string[][] cases={new[]{"1.0.0","20190102.3","1.0.19.5203"},new[]{"2.1.800","20190314.5","2.108.19.16405"},new[]{"65535.654.9999","20991231.99","65535.65499.9999.63199"}};
foreach(var c in cases){var t=new CalculateAssemblyAndFileVersions{VersionPrefix=c[0],BuildNumber=c[1]};if(!t.Execute()||t.FileVersion!=c[2])throw new Exception("Original task vector");}
foreach(var v in new[]{"1.1.0","4.7.0"}) {var t=new CalculateAssemblyAndFileVersions{VersionPrefix=v,BuildNumber=args[0]};if(!t.Execute())throw new Exception("Source date task");Console.WriteLine(v+" "+t.FileVersion);}return 0;}}''')
project(version/'Build.csproj',dict(TargetFramework='net8.0',OutputType='Exe',AssemblyName='VersionCheck'),[program,here/'inputs/arcade-CalculateAssemblyAndFileVersions.cs'])
tree=E.parse(version/'Build.csproj');group=E.SubElement(tree.getroot(),'ItemGroup')
for name in ['Microsoft.Build.Framework','Microsoft.Build.Utilities.Core','NuGet.Versioning']:
    e=E.SubElement(group,'Reference',Include=name);E.SubElement(e,'HintPath').text=native(Path('/clang64/lib/dotnet/sdk/8.0.131')/(name+'.dll'))
tree.write(version/'Build.csproj',encoding='utf-8',xml_declaration=True)
build(version/'Build.csproj',consumer/'version-build.log')
run([dotnet,native(version/'bin/Release/net8.0/VersionCheck.dll'),seed],consumer/'version-run.log')
lines=(consumer/'version-run.log').read_text().splitlines()
assert lines==['1.1.0 '+records['netstandard']['file_version'],'4.7.0 '+records['System.Runtime']['file_version']],lines

# Stage only owned reference bytes, then direct this consumer's SDK to that pack root.
if len(sys.argv)==4:
    ref=selected_pack/'ref/netstandard2.1';ref.mkdir(parents=True)
    for p in (out/'ref').glob('*.dll'):(ref/p.name).write_bytes(p.read_bytes())
    data=selected_pack/'data';data.mkdir()
    framework=E.Element('FileList',Name='.NET Standard 2.1')
    for n,v in sorted(metadata['results'].items()):
        if not records[n]['package_asset']:continue
        E.SubElement(framework,'File',Type='Managed',Path='ref/netstandard2.1/'+n+'.dll',AssemblyName=n,PublicKeyToken=v['token'],AssemblyVersion=v['version'],FileVersion=records[n]['file_version'])
    E.indent(framework);E.ElementTree(framework).write(data/'FrameworkList.xml',encoding='utf-8',xml_declaration=True)
    (data/'PackageOverrides.txt').write_text('')
    (data/'PlatformManifest.txt').write_text(''.join(n+'.dll|NETStandard.Library.Ref|'+v['assembly_version']+'|'+v['file_version']+'\n' for n,v in sorted(records.items()) if v['package_asset']))
assert {p.name for p in (selected_pack/'ref/netstandard2.1').glob('*.dll')}=={p.name for p in (out/'ref').glob('*.dll')}
for p in (out/'ref').glob('*.dll'):assert p.read_bytes()==(selected_pack/'ref/netstandard2.1'/p.name).read_bytes(),p.name
packs=consumer/'packs';target=packs/'NETStandard.Library.Ref/2.1.0'
target.mkdir(parents=True)
import shutil
for d in ['ref','data']:shutil.copytree(selected_pack/d,target/d)
library=consumer/'library';library.mkdir()
project(library/'Build.csproj',dict(TargetFramework='netstandard2.1',AssemblyName='Standard21Consumer',LangVersion='8.0',NetCoreTargetingPackRoot=native(packs)),[here/'inputs/Consumer.cs'])
tree=E.parse(library/'Build.csproj')
capture=E.SubElement(tree.getroot(),'Target',Name='CaptureReferencePaths',BeforeTargets='CoreCompile')
E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)references.txt',Lines="@(ReferencePath->'%(FullPath)')",Overwrite='true')
tree.write(library/'Build.csproj',encoding='utf-8',xml_declaration=True)
build(library/'Build.csproj',consumer/'library-build.log')
assets=json.loads((library/'obj/project.assets.json').read_text())
assert not assets['libraries'],assets['libraries']
refs=(library/'obj/Release/netstandard2.1/references.txt').read_text(encoding='utf-8-sig').splitlines()
assert len(refs)==121 and all('/packs/NETStandard.Library.Ref/2.1.0/ref/netstandard2.1/' in p.replace('\\','/') for p in refs),refs
runner=consumer/'runner';runner.mkdir()
code=runner/'Run.cs';code.write_text('using System;class Program {static int Main(){var s=Standard21Consumer.Run().GetAwaiter().GetResult();if(s!="42:1")throw new Exception(s);Console.WriteLine("PASS original source Standard2.1 Span/Range/async enumeration/disposal Unicode consumer: "+s);return 0;}}')
project(runner/'Build.csproj',dict(TargetFramework='net8.0',OutputType='Exe',AssemblyName='RunStandard21Consumer'),[code])
tree=E.parse(runner/'Build.csproj');E.SubElement(E.SubElement(tree.getroot(),'ItemGroup'),'ProjectReference',Include='../library/Build.csproj');tree.write(runner/'Build.csproj',encoding='utf-8',xml_declaration=True)
build(runner/'Build.csproj',consumer/'runner-build.log')
run([dotnet,native(runner/'bin/Release/net8.0/RunStandard21Consumer.dll')],consumer/'run.log')
negative=consumer/'RejectNewApi.cs';negative.write_text('public class RejectNewApi {public System.Threading.Lock Value;}')
rsp=consumer/'negative.rsp';rsp.write_text('\n'.join(['/nostdlib+','/target:library','/out:"'+native(consumer/'negative.dll')+'"',*['/reference:"'+native(p)+'"' for p in sorted((selected_pack/'ref/netstandard2.1').glob('*.dll'))],'"'+native(negative)+'"'])+'\n')
compiler=Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap/CompilerHost.dll')
negative_code=run([dotnet,native(compiler),'-noconfig','@'+native(rsp)],consumer/'negative.log',False)
assert negative_code!=0 and 'Lock' in (consumer/'negative.log').read_text()
result=dict(original_inputs_verified=len(verified),metadata=metadata,consumer_exit_code=0,actual_source_reference_paths=121,negative_new_api_exit_code=negative_code,original_arcade_version_task_and_three_vectors_passed=True,formal_pacman_installed=len(sys.argv)==5,full_dependency_goal_complete=False)
(consumer/'results.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS original Standard2.1 sources, complete forwards/metadata, original version task, fresh SDK consumer and newer-API rejection')
