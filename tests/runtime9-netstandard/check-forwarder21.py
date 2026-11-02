"""Build the original runtime9 AsyncInterfaces Standard2.1 target against the owned source pack.

This is a precursor to recipe integration, not proof that the installed runtime9
NuGet already includes the new forwarding target.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

archive, out, keyfile = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(),out
out.mkdir(parents=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive)=='32755d528ead386762fb9da054249f6151ac78ef6a92f437044838cd0ab00def'
pack=Path('/clang64/lib/dotnet/packs/NETStandard.Library.Ref/2.1.0')
assert len(list((pack/'ref/netstandard2.1').glob('*.dll')))==121
rootnative=subprocess.check_output(['cygpath','-am',str(out)],text=True).strip()
def native(p):
    p=p.resolve()
    if p.is_relative_to(out):return rootnative+'/'+p.relative_to(out).as_posix()
    return subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
base='src/libraries/Microsoft.Bcl.AsyncInterfaces/src/'
wanted={base+'Microsoft.Bcl.AsyncInterfaces.csproj',base+'Microsoft.Bcl.AsyncInterfaces.Forwards.cs',
        'src/libraries/System.Private.CoreLib/src/System/Diagnostics/CodeAnalysis/NullableAttributes.cs',
        'src/libraries/Directory.Build.props','src/libraries/Directory.Build.targets','LICENSE.TXT','THIRD-PARTY-NOTICES.TXT'}
original={}
with tarfile.open(archive) as t:
    assert t.pax_headers['comment']=='9d5a6a9aa463d6d10b0b0ba6d5982cc82f363dc3'
    for m in t:
        name=m.name.partition('/')[2]
        if m.isfile() and name in wanted:
            p=out/'source'/name;p.parent.mkdir(parents=True,exist_ok=True)
            data=t.extractfile(m).read();p.write_bytes(data);original[name]=hashlib.sha256(data).hexdigest()
assert set(original)==wanted
source=out/'source'
upstream=source/base/'Microsoft.Bcl.AsyncInterfaces.csproj'
tree=E.parse(upstream);tree.getroot().attrib.pop('Sdk')
for item in tree.iter():
    if item.tag=='Compile':
        item.set('Include',native(upstream.parent/item.get('Include').replace('\\','/')) if '$(' not in item.get('Include') else item.get('Include'))
E.ElementTree(tree.getroot()).write(out/'upstream.proj',encoding='utf-8',xml_declaration=True)
key=bytes.fromhex(keyfile.read_text());assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='cc7b13ffcd2ddd51'
(out/'Open.pubkey').write_bytes(key)
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),
         DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
dotnet='/clang64/lib/dotnet/dotnet.exe'
def run(cmd,log):
    with log.open('w') as f:r=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
    assert r.returncode==0,(cmd,log)
def project(path,properties,files):
    root=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(root,'PropertyGroup')
    for k,v in dict(EnableDefaultItems='false',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableNETAnalyzers='false',NuGetAudit='false',UseAppHost='false',UseSharedCompilation='false',**properties).items():E.SubElement(pg,k).text=v
    ig=E.SubElement(root,'ItemGroup')
    for f in files:E.SubElement(ig,'Compile',Include=native(f))
    return root,pg,ig
name='Microsoft.Bcl.AsyncInterfaces'
root,pg,ig=project(out/'Build.csproj',dict(TargetFramework='netstandard2.1',AssemblyName=name,PackageId=name,Version='9.0.0',AssemblyVersion='9.0.0.0',FileVersion='9.0.0.0',
    InformationalVersion='9.0.0+9d5a6a9aa463d6d10b0b0ba6d5982cc82f363dc3',Nullable='enable',LangVersion='preview',SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile=native(out/'Open.pubkey'),
    NetFrameworkMinimum='net462',CoreLibSharedDir=native(source/'src/libraries/System.Private.CoreLib/src')+'/',
    CscToolPath=native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')),CscToolExe='csc50.cmd',
    GenerateAssemblyConfigurationAttribute='false',GenerateNeutralResourcesLanguageAttribute='false'),[])
E.SubElement(root,'Import',Project='upstream.proj')
after=E.SubElement(root,'PropertyGroup');E.SubElement(after,'TargetFrameworks').text=''
E.SubElement(ig,'Compile',Include=native(source/'src/libraries/System.Private.CoreLib/src/System/Diagnostics/CodeAnalysis/NullableAttributes.cs'))
for typ,val,literal in [('System.CLSCompliantAttribute','true',True),('System.Reflection.AssemblyDefaultAliasAttribute',name,False),('System.Runtime.InteropServices.DefaultDllImportSearchPathsAttribute','System.Runtime.InteropServices.DllImportSearchPath.AssemblyDirectory | System.Runtime.InteropServices.DllImportSearchPath.System32',True)]:
    a=E.SubElement(ig,'AssemblyAttribute',Include=typ);E.SubElement(a,'_Parameter1').text=val
    if literal:E.SubElement(a,'_Parameter1_IsLiteral').text='true'
for tag in ['PreferInbox','Serviceable']:E.SubElement(ig,'AssemblyMetadata',Include=tag,Value='True')
capture=E.SubElement(root,'Target',Name='CaptureOriginalInputs',BeforeTargets='CoreCompile')
for kind in ['Compile','ReferencePath','PackageReference']:
    E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)'+kind+'.txt',Lines='@('+kind+"->'%(FullPath)')",Overwrite='true')
E.indent(root);E.ElementTree(root).write(out/'Build.csproj',encoding='utf-8',xml_declaration=True)
(out/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>')
run([dotnet,'build',native(out/'Build.csproj'),'-c','Release','--configfile',native(out/'NuGet.config'),'-v:minimal'],out/'build.log')
actual=(out/'obj/Release/netstandard2.1/Compile.txt').read_text(encoding='utf-8-sig').splitlines()
selected={p.replace('\\','/')[len(rootnative)+1:] for p in actual if p.replace('\\','/').lower().startswith((rootnative+'/source/').lower())}
assert selected=={'source/'+base+'Microsoft.Bcl.AsyncInterfaces.Forwards.cs','source/src/libraries/System.Private.CoreLib/src/System/Diagnostics/CodeAnalysis/NullableAttributes.cs'},selected
refs=(out/'obj/Release/netstandard2.1/ReferencePath.txt').read_text(encoding='utf-8-sig').splitlines()
assert len(refs)==121 and all('/packs/NETStandard.Library.Ref/2.1.0/ref/netstandard2.1/' in p.replace('\\','/') for p in refs),refs
assets=json.loads((out/'obj/project.assets.json').read_text());assert not assets['libraries']
result=dict(original_inputs_sha256=original,source_compile_inputs=sorted(selected),actual_source_reference_paths=121,
    forwarding_declarations=len(re.findall('TypeForwardedTo', (source/base/'Microsoft.Bcl.AsyncInterfaces.Forwards.cs').read_text())),
    forwarder_sha256=sha(out/'bin/Release/netstandard2.1/Microsoft.Bcl.AsyncInterfaces.dll'),build_exit_code=0,
    formal_runtime9_nuget_contains_forwarder=False,full_dependency_goal_complete=False)
expected=[]
for value in re.findall(r'TypeForwardedTo\(typeof\((.*?)\)\)',(source/base/'Microsoft.Bcl.AsyncInterfaces.Forwards.cs').read_text()):
    expected.append(re.sub(r'<(,*)>',lambda m:'`'+str(len(m[1])+1),value))
assert len(expected)==10
(out/'expected-forwards.json').write_text(json.dumps(expected)+'\n')
tool=out/'metadata';tool.mkdir()
root,pg,ig=project(tool/'Build.csproj',dict(TargetFramework='net8.0',OutputType='Exe',AssemblyName='CheckForwarder21'),[Path(__file__).resolve().parent/'CheckForwarder21.cs'])
E.indent(root);E.ElementTree(root).write(tool/'Build.csproj',encoding='utf-8',xml_declaration=True)
run([dotnet,'build',native(tool/'Build.csproj'),'-c','Release','--configfile',native(out/'NuGet.config'),'-v:minimal'],out/'metadata-build.log')
run([dotnet,native(tool/'bin/Release/net8.0/CheckForwarder21.dll'),native(out/'bin/Release/netstandard2.1/Microsoft.Bcl.AsyncInterfaces.dll'),native(out/'expected-forwards.json')],out/'metadata-results.json')
result['metadata_and_runtime']=json.loads((out/'metadata-results.json').read_text())
(out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS original AsyncInterfaces Standard2.1 target builds against 121 installed source references; recipe integration remains open')
