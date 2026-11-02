"""Audit every original asset and scope, compile consumers and execute source arithmetic."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

feed,out,prefix,compiler=(Path(p).resolve() for p in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).parent;name='System.Runtime.Numerics';dotnet=prefix/'lib/dotnet/dotnet.exe';policy=json.loads((here/'inputs/published-package-policy.json').read_text())[name];commands=[]
env=dict(os.environ,DOTNET_CLI_HOME=(out/'cli-home').as_posix(),NUGET_PACKAGES=(out/'cache').as_posix(),MSBuildEnableWorkloadResolver='false')
def run(label,args,required=True):
    c=[str(p) for p in args];r=subprocess.run(c,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120);(out/(label+'.log')).write_bytes(r.stdout);commands.append(dict(command=c,exit_code=r.returncode));assert not required or r.returncode==0,(label,r.stdout.decode(errors='replace')[-6000:]);return r
run('inspector-build',[sys.executable,here/'build-inspector.py',out/'inspector',prefix]);run('forwarder-build',[sys.executable,here/'build-forwarder-inspector.py',out/'forwarders',prefix])
(out/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
def tool(label,source,nuget=False,nullable=True):
    folder=out/label;folder.mkdir();t=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(t,'PropertyGroup')
    for n,v in dict(TargetFramework='net8.0',OutputType='Exe',AssemblyName=label,UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='enable' if nullable else 'disable',TreatWarningsAsErrors='true',CscToolPath=(prefix/'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap').as_posix(),CscToolExe='csc50.cmd').items():E.SubElement(pg,n).text=v
    ig=E.SubElement(t,'ItemGroup');E.SubElement(ig,'Compile',Include=(here/'inputs'/source).as_posix())
    if nuget:
        for n in ['NuGet.Packaging','NuGet.Frameworks','NuGet.Versioning','NuGet.Common']:E.SubElement(ig,'Reference',Include=n,HintPath=(prefix/'lib/dotnet/sdk/8.0.131'/(n+'.dll')).as_posix())
    E.indent(t);E.ElementTree(t).write(folder/(label+'.csproj'),encoding='utf-8',xml_declaration=True);run(label+'-build',[dotnet,'build',folder/(label+'.csproj'),'-c','Release','--configfile',out/'NuGet.config','-p:UseSharedCompilation=false','-v:minimal']);return folder/'bin/Release/net8.0'/(label+'.dll')
reader=tool('ReadResources','ReadResources.cs',nullable=False);semantics=tool('CheckNuGet','CheckNuGet.cs',nuget=True);executor=tool('Host','Host.cs')
package=next(p for p in feed.glob('*.nupkg') if p.name.casefold()==(name+'.4.3.0.nupkg').casefold());payload=out/'payload';resources=json.loads((here/'inputs/baselines1/resource-data.json').read_text());records={};canon=lambda rows:sorted(json.dumps(r,sort_keys=True) for r in rows)
with zipfile.ZipFile(package) as z:
    expected=set(policy['reference_DLL_sha256'])|set(policy['original_data_sha256']);actual={n for n in z.namelist() if n.startswith(('ref/','lib/','runtimes/')) or n in policy['original_data_sha256']};assert actual==expected
    assert {n for n in z.namelist() if n.endswith('.dll')}==set(policy['reference_DLL_sha256'])
    for p,h in policy['original_data_sha256'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h,p
    assert z.read('lib/netcore50/'+name+'.dll')==z.read('lib/netstandard1.3/'+name+'.dll');assert z.read('ref/netcore50/'+name+'.dll')==z.read('ref/netstandard1.1/'+name+'.dll')
    for path in policy['reference_DLL_sha256']:
        p=payload/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(path))
for path in policy['reference_DLL_sha256']:
    kind,tfm,_=path.split('/');label=kind+'-'+tfm;p=out/label;p.mkdir();dll=payload/path
    run(label+'-metadata',[dotnet,out/'inspector/bin/Release/net8.0/Inspect.dll',p/'metadata.json',dll]);got=json.loads((p/'metadata.json').read_text())[name+'.dll'];want=json.loads((here/'inputs/baselines1'/(label+'.json')).read_text())[name+'.dll']
    assert got['identity']==want['identity'] and got['api']==want['api'] and set(got['references'])==set(want['references']) and canon(got['attributes'])==canon(want['attributes']),label
    actual=json.loads(run(label+'-resources',[dotnet,reader,dll]).stdout)[0];expected=next(r for r in resources if '/'+kind+'/'+tfm+'/' in r['file'])
    for key in ['name','version','public_key','public_key_token','attributes','resources','embedded_nonresource_blob_hashes','exported_types','native_version','references']:assert actual[key]==expected[key],(label,key)
    run(label+'-exports',[dotnet,out/'forwarders/bin/Release/net8.0/Forwarders.dll',p/'exports.json',dll]);a=json.loads((p/'exports.json').read_text())[0];b=json.loads((here/'inputs/baselines1'/(label+'-exports.json')).read_text())[0]
    for key in ['identity','reference_only','assembly_references','exported_types']:assert a[key]==b[key],(label,key)
    refs=[prefix/'lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts/System.Runtime'/('4.0.0.0' if kind=='ref' else '4.0.20.0')/'System.Runtime.dll',dll]
    args=['/nostdlib+','/target:exe','/langversion:7.3','/optimize+','/deterministic+','/warnaserror+','/nowarn:1701,1702','/out:"'+(p/'Probe.dll').as_posix()+'"']+['/reference:"'+r.as_posix()+'"' for r in refs]+['"'+(here/'inputs/Probe.cs').as_posix()+'"']
    rsp=p/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');run(label+'-consumer',[dotnet,compiler/'csc.dll','-noconfig','@'+str(rsp)]);(p/'Probe.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net8.0','framework':{'name':'Microsoft.NETCore.App','version':'8.0.31'}}})+'\n');run(label+'-consumer-run',[dotnet,p/'Probe.dll'])
    records[label]=dict(identity=got['identity'],API_entries=len(got['api']),references=got['references'],source_DLL_SHA256=hashlib.sha256(dll.read_bytes()).hexdigest(),all_original_metadata_native_resources_exports_and_consumer_verified=True);print('PASS original metadata and typed consumer:',label,flush=True)
# Compile an alias-bound runner against the actual implementation, not the host's forwarded Numerics types.
folder=out/'runtime';folder.mkdir();t=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(t,'PropertyGroup')
for n,v in dict(TargetFramework='net8.0',OutputType='Exe',AssemblyName='Run',UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='enable',TreatWarningsAsErrors='true',CscToolPath=(prefix/'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap').as_posix(),CscToolExe='csc50.cmd').items():E.SubElement(pg,n).text=v
ig=E.SubElement(t,'ItemGroup');E.SubElement(ig,'Compile',Include=(here/'inputs/Run.cs').as_posix());E.SubElement(ig,'Reference',Include=name,HintPath=(payload/'lib/netstandard1.3'/(name+'.dll')).as_posix(),Aliases='candidate',Private='true');E.indent(t);E.ElementTree(t).write(folder/'Run.csproj',encoding='utf-8',xml_declaration=True)
target=E.SubElement(t,'Target',Name='RemoveHostNumericsForwarder',BeforeTargets='ResolveAssemblyReferences');items=E.SubElement(target,'ItemGroup');E.SubElement(items,'Reference',Remove='@(Reference)',Condition="'%(Reference.Filename)' == 'System.Runtime.Numerics' and '%(Reference.FrameworkReferenceName)' == 'Microsoft.NETCore.App'");E.indent(t);E.ElementTree(t).write(folder/'Run.csproj',encoding='utf-8',xml_declaration=True)
run('runtime-build',[dotnet,'build',folder/'Run.csproj','-c','Release','--configfile',out/'NuGet.config','-p:UseSharedCompilation=false','-v:minimal']);run('runtime-arithmetic',[dotnet,executor,folder/'bin/Release/net8.0/Run.dll',payload/'lib/netstandard1.3'/(name+'.dll')]);run('NuGet-semantics',[dotnet,semantics,package,here/'inputs/published-package-policy.json'])
installed=(prefix/'lib/dotnet/library-packs').resolve();same=installed.as_posix().casefold()==feed.as_posix().casefold();t=E.Element('configuration');sources=E.SubElement(t,'packageSources');E.SubElement(sources,'clear');E.SubElement(sources,'add',key='candidate',value=feed.as_posix())
if not same:E.SubElement(sources,'add',key='installed',value=installed.as_posix())
mapping=E.SubElement(t,'packageSourceMapping');candidate=E.SubElement(mapping,'packageSource',key='candidate');E.SubElement(candidate,'package',pattern=name);E.SubElement(candidate if same else E.SubElement(mapping,'packageSource',key='installed'),'package',pattern='*');E.indent(t);E.ElementTree(t).write(out/'restore.config',encoding='utf-8',xml_declaration=True)
restores={}
for label,tfm,meta in [('own-ns11','netstandard1.1',False),('own-ns13','netstandard1.3',False),('own-netcore50','netcore50',False),('standard161','netstandard1.3',True)]:
    folder=out/label;folder.mkdir();t=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(t,'PropertyGroup')
    for n,v in dict(TargetFramework=tfm,EnableDefaultItems='false',DisableImplicitFrameworkReferences='true',AutomaticallyUseReferenceAssemblyPackages='false',NuGetAudit='false',TreatWarningsAsErrors='true').items():E.SubElement(pg,n).text=v
    if tfm=='netcore50':
        E.SubElement(pg,'TargetFrameworkIdentifier').text='.NETCore';E.SubElement(pg,'TargetFrameworkVersion').text='v5.0';E.SubElement(pg,'UseTargetPlatformAsNuGetTargetMoniker').text='false';E.SubElement(pg,'NuGetTargetMoniker').text='.NETCore,Version=v5.0'
    E.SubElement(E.SubElement(t,'ItemGroup'),'PackageReference',Include='NETStandard.Library' if meta else name,Version='[1.6.1]' if meta else '[4.3.0]');E.indent(t);E.ElementTree(t).write(folder/'Probe.csproj',encoding='utf-8',xml_declaration=True);r=run(label+'-restore',[dotnet,'restore',folder/'Probe.csproj','--configfile',out/'restore.config','-v:minimal'],required=not meta);assets=json.loads((folder/'obj/project.assets.json').read_text());logs=assets.get('logs',[]);assert all(d['code']=='NU1101' for d in logs),logs;assert not any(d.get('libraryId','').casefold()==name.casefold() for d in logs)
    assert (out/'cache'/name.lower()/'4.3.0'/package.name.lower()).read_bytes()==package.read_bytes()
    restores[label]=dict(exit_code=r.returncode,diagnostics=logs,missing_IDs=sorted({d['libraryId'] for d in logs}));print(label,'restore exit',r.returncode,'remaining IDs',len(restores[label]['missing_IDs']),flush=True)
(out/'results.json').write_text(json.dumps(dict(commands=commands,profiles=records,source_NuGet_SHA256=hashlib.sha256(package.read_bytes()).hexdigest(),original_reference_API_entries=192,original_runtime_API_entries=192,original_netcore50_aliases_verified=True,all_original_assets_aliases_data_dependency_and_framework_semantics_verified=True,actual_source_BigInteger_Complex_arithmetic_resources_and_errors_verified=True,fresh_restores=restores,original_Framework_runtime_execution_verified=False,full_dependency_goal_complete=False),indent=2)+'\n')
