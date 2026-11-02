"""Exercise unmodified packaged targets, including expected rejection paths."""
from pathlib import Path
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

feed,check=(Path(p).resolve() for p in sys.argv[1:]);assert not check.exists();check.mkdir()
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
with zipfile.ZipFile(feed/'polysharp.1.15.0.nupkg' if (feed/'polysharp.1.15.0.nupkg').exists() else feed/'PolySharp.1.15.0.nupkg') as z:
    targets=check/'PolySharp.targets';targets.write_bytes(z.read('buildTransitive/PolySharp.targets'))
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),
    DOTNET_CLI_HOME=native(check/'cli-home'),NUGET_PACKAGES=native(check/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
dotnet='/clang64/lib/dotnet/dotnet.exe';commands=[]
def run(label,args,code=0,diagnostic=None):
    with (check/(label+'.log')).open('w') as log:result=subprocess.run([dotnet,*args],env=env,stdout=log,stderr=subprocess.STDOUT)
    text=(check/(label+'.log')).read_text()
    assert result.returncode==code,(label,result.returncode,text[-4000:])
    if diagnostic:assert diagnostic in text,(label,text)
    commands.append(dict(label=label,command=[dotnet,*args],exit_code=result.returncode,expected_exit_code=code,expected_diagnostic=diagnostic))

# This assembly is only a metadata fixture for the targets' version reader.
# It is not a replacement compiler or a claim that an old compiler was executed.
stub=check/'old-version-fixture';stub.mkdir()
(stub/'Fixture.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><AssemblyName>Microsoft.Build.Tasks.CodeAnalysis</AssemblyName><AssemblyVersion>4.2.0.0</AssemblyVersion><NuGetAudit>false</NuGetAudit><TreatWarningsAsErrors>true</TreatWarningsAsErrors></PropertyGroup></Project>\n')
(stub/'Marker.cs').write_text('internal class VersionMetadataFixture {}\n')
config=check/'NuGet.config';config.write_text('<configuration><packageSources><clear/><add key="source" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources></configuration>\n')
run('build-version-fixture',['build',native(stub/'Fixture.csproj'),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal'])
stub_targets=stub/'bin/Release/net8.0/Microsoft.CSharp.Core.targets';stub_targets.write_text('<Project/>\n')
current=Path('/clang64/lib/dotnet/sdk/8.0.131/Roslyn/Microsoft.CSharp.Core.targets');assert current.exists()
cases=[('old',native(stub_targets),'_PolySharpRemoveAnalyzersForRoslyn3',1,'POLYSPCFG0001',None),
       ('current',native(current),'_PolySharpRemoveAnalyzersForRoslyn3',0,None,'owned-analyzer'),
       ('missing','','_PolySharpRemoveAnalyzersForRosynNotFound',0,None,'')]
for label,compiler,target,code,diagnostic,expected in cases:
    path=check/(label+'.proj');tree=E.Element('Project');pg=E.SubElement(tree,'PropertyGroup')
    E.SubElement(pg,'CSharpCoreTargetsPath').text=compiler
    items=E.SubElement(tree,'ItemGroup');analyzer=E.SubElement(items,'Analyzer',Include='owned-analyzer');E.SubElement(analyzer,'NuGetPackageId').text='PolySharp'
    E.SubElement(tree,'Import',Project=native(targets))
    capture=E.SubElement(tree,'Target',Name='Probe',DependsOnTargets=target)
    result_path=check/(label+'.txt')
    E.SubElement(capture,'WriteLinesToFile',File=native(result_path),Lines='@(Analyzer)',Overwrite='true')
    E.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)
    run(label,['msbuild',native(path),'-t:Probe','-nologo','-v:minimal'],code,diagnostic)
    if expected is not None:assert result_path.read_text().strip()==expected

for label,props,item,code in [('restore-flag',{'RestorePackagesConfig':'true'},False,1),('restore-style',{'RestoreProjectStyle':'PackagesConfig'},False,1),('none-item',{},True,1),('package-reference',{'RestoreProjectStyle':'PackageReference'},False,0),('sdk-project',{'UsingMicrosoftNetSDK':'true','RestorePackagesConfig':'true'},False,0)]:
    path=check/(label+'.proj');tree=E.Element('Project');pg=E.SubElement(tree,'PropertyGroup')
    for name,value in props.items():E.SubElement(pg,name).text=value
    if item:E.SubElement(E.SubElement(tree,'ItemGroup'),'None',Include='packages.config')
    E.SubElement(tree,'Import',Project=native(targets));E.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)
    run(label,['msbuild',native(path),'-t:_PolySharpWarnForPackagesConfigUse','-warnAsError','-nologo','-v:minimal'],code,'POLYSPCFG0002' if code else None)

path=check/'visible-properties.proj';tree=E.Element('Project');pg=E.SubElement(tree,'PropertyGroup')
for name,value in [('PolySharpExcludeGeneratedTypes','System.Index;\nSystem.Range'),('PolySharpIncludeGeneratedTypes','System.TypeA;\r\nSystem.TypeB')]:E.SubElement(pg,name).text=value
E.SubElement(tree,'Import',Project=native(targets));target=E.SubElement(tree,'Target',Name='Probe',DependsOnTargets='ConfigurePolySharpMSBuildProperties')
E.SubElement(target,'WriteLinesToFile',File=native(check/'visible.txt'),Lines='@(CompilerVisibleProperty)',Overwrite='true')
E.SubElement(target,'WriteLinesToFile',File=native(check/'normalized.txt'),Lines='$(PolySharpExcludeGeneratedTypes)|$(PolySharpIncludeGeneratedTypes)',Overwrite='true')
E.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)
run('visible-properties',['msbuild',native(path),'-t:Probe','-nologo','-v:minimal'])
assert len((check/'visible.txt').read_text().splitlines())==6
assert (check/'normalized.txt').read_text().strip()=='System.Index,System.Range|System.TypeA,System.TypeB'
(check/'results.json').write_text(json.dumps(dict(commands=commands,minimum_compiler_metadata_guard=True,old_version_fixture_is_not_an_executed_compiler=True,missing_compiler_removes_analyzer=True,legacy_project_guards=True,compiler_visible_properties_and_normalization=True,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original compiler-version/missing-compiler/legacy guards and visible-property normalization')
