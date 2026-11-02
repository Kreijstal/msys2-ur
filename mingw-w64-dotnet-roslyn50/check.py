"""Verify real Roslyn5.0 language/API/resource behavior from a fresh source feed."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile
from collections import Counter

resume='--resume' in sys.argv[1:]
args=[p for p in sys.argv[1:] if p!='--resume']
root,out,check=(Path(p).resolve() for p in args[:3])
installed=len(args)==4
selected_feed=Path(args[3]).resolve() if installed else out/'feed'
assert resume or not check.exists(), check
check.mkdir(parents=True,exist_ok=resume)
here=Path(__file__).resolve().parent
native_root=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
def native(path):
    path=Path(path).resolve()
    if path.is_relative_to(root):return native_root+'/'+path.relative_to(root).as_posix()
    return subprocess.check_output(['cygpath','-am',str(path)],text=True).strip()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((out/'source-inputs.json').read_text())
original=out/'roslyn-source'
coverage=dict(resource_sets=0,resource_values=0)
for name,record in source['projects'].items():
    expected_cultures=[]
    for filename in record['original_resources']:
        path=original/filename
        if path.suffix!='.resx':continue
        strings=len(list(E.parse(path).iter('data')))
        cultures=['']
        for translation in (path.parent/'xlf').glob(path.stem+'.*.xlf'):
            element=E.parse(translation).find('{urn:oasis:names:tc:xliff:document:1.2}file')
            cultures.append(element.get('target-language'))
        expected_cultures.extend(cultures)
        coverage['resource_sets']+=len(cultures)
        coverage['resource_values']+=len(cultures)*strings
    actual=[i for i in json.loads((out/'localization.json').read_text()) if i['assembly']==name]
    assert Counter(i['culture'] for i in actual)==Counter(expected_cultures),(name,'Original XLF coverage differs')
(check/'original-localization-coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
for name,record in source['projects'].items():
    for path,expected in record['original_cs'].items():assert sha(original/path)==expected,(name,path)
for suffix,name,language in [('common','Microsoft.CodeAnalysis','Core'),('csharp','Microsoft.CodeAnalysis.CSharp','CSharp')]:
    folder=original/'src/Compilers'/language/'Portable'
    (check/('api-'+suffix+'.txt')).write_text((folder/'PublicAPI.Shipped.txt').read_text().rstrip()+'\n'+(folder/'PublicAPI.Unshipped.txt').read_text().rstrip()+'\n')
    resources=[dict(assembly=item['assembly'],resource=item['logical_name'],culture=item['culture'],strings=item['strings'])
               for item in json.loads((out/'localization.json').read_text()) if item['assembly']==name]
    (check/('localization-'+suffix+'.json')).write_text(json.dumps(resources,ensure_ascii=False,indent=2)+'\n')
config=E.Element('configuration');sources=E.SubElement(config,'packageSources');E.SubElement(sources,'clear')
for i,feed in enumerate([selected_feed,Path('/clang64/lib/dotnet/library-packs')]):E.SubElement(sources,'add',key='source'+str(i),value=native(feed))
E.ElementTree(config).write(check/'NuGet.config',encoding='utf-8',xml_declaration=True)
standard=check/'standard-consumer';standard.mkdir(exist_ok=resume)
standard_tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');properties=E.SubElement(standard_tree,'PropertyGroup')
for k,v in dict(TargetFramework='netstandard2.0',AssemblyName='StandardRoslynConsumer',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',UseSharedCompilation='false',WarningsAsErrors='NU1608').items():E.SubElement(properties,k).text=v
standard_items=E.SubElement(standard_tree,'ItemGroup')
E.SubElement(standard_items,'Compile',Include=native(here/'inputs/StandardConsumer.cs'))
E.SubElement(standard_items,'PackageReference',Include='Microsoft.CodeAnalysis.CSharp',Version='[5.0.0]')
E.ElementTree(standard_tree).write(standard/'Build.csproj',encoding='utf-8',xml_declaration=True)
tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',OutputType='Exe',UseAppHost='false',EnableDefaultItems='false',
                EnableNETAnalyzers='false',NuGetAudit='false',Nullable='enable',LangVersion='preview',
                CscToolPath=native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')),CscToolExe='csc50.cmd').items():E.SubElement(pg,k).text=v
E.SubElement(pg,'WarningsAsErrors').text='NU1608'
ig=E.SubElement(tree,'ItemGroup')
for file in ['Roslyn50Checks.cs','CheckApi.cs']:E.SubElement(ig,'Compile',Include=native(here/'inputs'/file))
E.SubElement(ig,'PackageReference',Include='Microsoft.CodeAnalysis.CSharp',Version='[5.0.0]')
E.SubElement(ig,'ProjectReference',Include='standard-consumer/Build.csproj')
E.ElementTree(tree).write(check/'Check.csproj',encoding='utf-8',xml_declaration=True)
env=dict(os.environ,DOTNET_CLI_HOME=native(check/'cli-home'),NUGET_PACKAGES=native(check/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
dotnet='/clang64/lib/dotnet/dotnet.exe'
with (check/'build.log').open('w') as log:
    subprocess.run([dotnet,'build',native(check/'Check.csproj'),'-c','Release','--configfile',native(check/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
binary=check/'bin/Release/net8.0';packages={}
for name in ['Microsoft.CodeAnalysis.Common','Microsoft.CodeAnalysis.CSharp']:
    package=selected_feed/(name.lower()+'.5.0.0.nupkg')
    if not package.exists():package=selected_feed/(name+'.5.0.0.nupkg')
    assert package.read_bytes()==(out/'feed'/(name+'.5.0.0.nupkg')).read_bytes()
    assert (check/'cache'/name.lower()/'5.0.0'/(name.lower()+'.5.0.0.nupkg')).read_bytes()==package.read_bytes()
    with zipfile.ZipFile(package) as z:
        for path in z.namelist():
            if path.startswith('lib/netstandard2.0/') and path.endswith('.dll'):
                assert (binary/path.removeprefix('lib/netstandard2.0/')).read_bytes()==z.read(path),(name,path)
    packages[name]=sha(package)
refs=subprocess.check_output(['cygpath','-am','/clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0'],text=True).strip()
command=[dotnet,native(binary/'Check.dll'),refs,
         *[native(check/file) for file in ['api-common.txt','api-csharp.txt','localization-common.json','localization-csharp.json','original-localization-coverage.json']]]
with (check/'run.log').open('w') as log:
    result=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
(check/'run.exit').write_text(str(result.returncode)+'\n')
assert result.returncode==0,(result.returncode,check/'run.log')
(check/'results.json').write_text(json.dumps(dict(runtime_checks_command=command,runtime_checks_exit_code=0,
    exact_source_package_and_localized_dll_bytes_match=True,source_package_sha256=packages,
    formal_pacman_installed=installed,source_workspaces414_built=False,source_roslyn44_built=False,source_targeting_generators10_complete=False,
    full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original netstandard2.0 Roslyn5.0 libraries: fresh C#13/emit/execute/compiler/analyzer/generator/public API/resource consumer')
