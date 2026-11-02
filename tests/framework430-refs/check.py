"""Audit all 13 original profiles, NuGet semantics and real source restore gaps."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

feed, out, prefix, compiler = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir(); here = Path(__file__).parent
policies=json.loads((here/'inputs/published-package-policy.json').read_text());profiles=json.loads((here/'inputs/baselines1/profiles.json').read_text());matrix=json.loads((here/'inputs/source-contract-build-matrix.json').read_text());resources=json.loads((here/'inputs/reference-data.json').read_text())
commands=[];env=dict(os.environ,DOTNET_CLI_HOME=(out/'cli-home').as_posix(),NUGET_PACKAGES=(out/'cache').as_posix(),MSBuildEnableWorkloadResolver='false');dotnet=prefix/'lib/dotnet/dotnet.exe'
def run(label,command,required=True):
 command=[str(p) for p in command];r=subprocess.run(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/(label+'.log')).write_bytes(r.stdout);commands.append(dict(command=command,exit_code=r.returncode));
 if required:assert r.returncode==0,(label,r.stdout.decode('utf-8',errors='replace')[-6000:])
 return r
run('inspector-build',[sys.executable,here/'build-inspector.py',out/'inspector',prefix]);run('forwarder-build',[sys.executable,here/'build-forwarder-inspector.py',out/'forwarders',prefix])
config=out/'NuGet.config';config.write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
def tool(name,source,nuget=False,cecil=False,nullable=True):
 folder=out/name;folder.mkdir();t=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(t,'PropertyGroup')
 for n,v in dict(TargetFramework='net8.0',OutputType='Exe',AssemblyName=name,UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='enable' if nullable else 'disable',TreatWarningsAsErrors='true',CscToolPath=(prefix/'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap').as_posix(),CscToolExe='csc50.cmd').items():E.SubElement(pg,n).text=v
 items=E.SubElement(t,'ItemGroup');E.SubElement(items,'Compile',Include=(here/'inputs'/source).as_posix())
 if nuget:
  for n in ['NuGet.Packaging','NuGet.Frameworks','NuGet.Versioning','NuGet.Common']:E.SubElement(items,'Reference',Include=n,HintPath=(prefix/'lib/dotnet/sdk/8.0.131'/(n+'.dll')).as_posix())
 if cecil:E.SubElement(items,'Reference',Include='Mono.Cecil',HintPath=(out/'inspector/Mono.Cecil.dll').as_posix())
 E.indent(t);E.ElementTree(t).write(folder/(name+'.csproj'),encoding='utf-8',xml_declaration=True);run(name+'-build',[dotnet,'build',folder/(name+'.csproj'),'-c','Release','--configfile',config,'-p:UseSharedCompilation=false','-v:minimal']);return folder/'bin/Release/net8.0'/(name+'.dll')
reader=tool('ReadResources','ReadResources.cs',nullable=False);semantics=tool('CheckNuGet','CheckNuGet.cs',nuget=True);debug=tool('CheckDebug','CheckDebug.cs',cecil=True)
records={};archives={};defines={'System.Collections':'COLLECTIONS','System.Diagnostics.Debug':'PROBE_DEBUG','System.Diagnostics.Tools':'TOOLS','System.Globalization':'GLOBALIZATION','System.Net.Primitives':'NET','System.Resources.ResourceManager':'RESOURCES','System.Runtime.Handles':'HANDLES','System.Threading.Timer':'TIMER'}
for name,policy in policies.items():
 package=next(p for p in feed.glob('*.nupkg') if p.name.lower()==(name+'.4.3.0.nupkg').lower());folder=out/name;folder.mkdir()
 with zipfile.ZipFile(package) as z:
  expected=set(policy['reference_DLL_sha256'])|set(policy['original_data_sha256']);actual={n for n in z.namelist() if n.startswith(('ref/','lib/')) or n in policy['original_data_sha256']};assert actual==expected
  assert {n for n in z.namelist() if n.endswith('.dll')}==set(policy['reference_DLL_sha256']);assert not any(n.endswith('.exe') for n in z.namelist())
  marker_count=sum(n.endswith('_._') for n in policy['original_data_sha256'])
  assert len([n for n in actual if n.endswith('_._')])==marker_count
  for path,digest in policy['original_data_sha256'].items():assert hashlib.sha256(z.read(path)).hexdigest()==digest,path
  for path,digest in policy['reference_DLL_sha256'].items():
   if '/netcore50/' in path:
    aliases=[n for n,h in policy['reference_DLL_sha256'].items() if h==digest and '/netcore50/' not in n];assert len(aliases)==1 and z.read(path)==z.read(aliases[0]);continue
   tfm=path.split('/')[1];label=name+'-'+tfm;p=folder/tfm;p.mkdir();dll=p/(name+'.dll');dll.write_bytes(z.read(path))
   run(label+'-inspect',[dotnet,out/'inspector/bin/Release/net8.0/Inspect.dll',p/'metadata.json',dll]);got=json.loads((p/'metadata.json').read_text())[name+'.dll'];want=json.loads((here/'inputs'/(label+'.json')).read_text())[name+'.dll']
   canon=lambda rows:sorted(json.dumps(r,sort_keys=True) for r in rows)
   assert got['identity']==want['identity'] and got['api']==want['api'] and set(got['references'])==set(want['references']) and canon(got['attributes'])==canon(want['attributes']),label
   assert any(a['type']=='System.Runtime.CompilerServices.ReferenceAssemblyAttribute' for a in got['attributes'])
   raw=run(label+'-resources',[dotnet,reader,dll]).stdout;actual_resources=json.loads(raw)[0];expected_resources=next(r for r in resources if r['name']==name and '/'+tfm+'/' in r['file'])
   for field in ['name','version','public_key','public_key_token','attributes','resources','embedded_nonresource_blob_hashes','exported_types','native_version','references']:assert actual_resources[field]==expected_resources[field],(label,field)
   run(label+'-exports',[dotnet,out/'forwarders/bin/Release/net8.0/Forwarders.dll',p/'exports.json',dll]);got_exports=json.loads((p/'exports.json').read_text())[0];wanted_exports=json.loads((here/'inputs/baselines1'/(label+'-exports.json')).read_text())[0]
   for field in ['identity','reference_only','assembly_references','exported_types']:assert got_exports[field]==wanted_exports[field],(label,field)
   closure=set()
   def select(ident):
    if ident in closure:return
    closure.add(ident)
    for ref in matrix[ident]['references']:
     n,v=ref.split(', Version=');select(n+'/'+v.split(',')[0])
   for ref in got['references']:
    n,v=ref.split(', Version=');select(n+'/'+v.split(',')[0])
   selected={}
   for ident in closure:
    n,v=ident.split('/')
    if n not in selected or tuple(map(int,v.split('.')))>tuple(map(int,selected[n].split('/')[1].split('.'))):selected[n]=ident
   refs=[prefix/'lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts'/ident/(ident.split('/')[0]+'.dll') for ident in sorted(selected.values())]
   args=['/nostdlib+','/target:library','/deterministic+','/warnaserror+','/nowarn:1701,1702','/define:'+defines[name],'/out:"'+(p/'Probe.dll').as_posix()+'"']+['/reference:"'+r.as_posix()+'"' for r in refs+[dll]]+['"'+(here/'inputs/Probe.cs').as_posix()+'"']
   rsp=p/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');run(label+'-compile',[dotnet,compiler/'csc.dll','-noconfig','@'+str(rsp)])
   if name=='System.Diagnostics.Debug':run(label+'-conditional',[dotnet,debug,here/'inputs/Debug-conditional-baselines.json',dll]);run(label+'-release',[dotnet,debug,'--consumer',p/'Probe.dll'])
   records[label]=dict(API_entries=len(got['api']),identity=got['identity'],source_DLL_sha256=hashlib.sha256(dll.read_bytes()).hexdigest(),all_original_metadata_resources_and_exports_verified=True,compile_consumer_passed=True)
   print('PASS original profile metadata, native/resources, exports and compile consumer:',label,len(got['api']),flush=True)
 run(name+'-NuGet',[dotnet,semantics,package,here/'inputs/published-package-policy.json']);archives[name]=dict(sha256=hashlib.sha256(package.read_bytes()).hexdigest(),markers=marker_count,original_data_aliases_and_dependency_framework_semantics_verified=True)
# Probe the real original metapackage closure with candidate-specific source mapping.
installed=(prefix/'lib/dotnet/library-packs').resolve();same=feed.as_posix().casefold()==installed.as_posix().casefold();t=E.Element('configuration');sources=E.SubElement(t,'packageSources');E.SubElement(sources,'clear');E.SubElement(sources,'add',key='candidate',value=feed.as_posix())
if not same:E.SubElement(sources,'add',key='installed',value=installed.as_posix())
mapping=E.SubElement(t,'packageSourceMapping');candidate=E.SubElement(mapping,'packageSource',key='candidate')
for name in policies:E.SubElement(candidate,'package',pattern=name)
E.SubElement(candidate if same else E.SubElement(mapping,'packageSource',key='installed'),'package',pattern='*');E.indent(t);E.ElementTree(t).write(out/'restore.config',encoding='utf-8',xml_declaration=True)
restores={}
for tfm in ['netstandard1.0','netstandard1.3']:
 folder=out/('restore-'+tfm);folder.mkdir();t=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(t,'PropertyGroup')
 for n,v in dict(TargetFramework=tfm,EnableDefaultItems='false',DisableImplicitFrameworkReferences='true',NuGetAudit='false',TreatWarningsAsErrors='true').items():E.SubElement(pg,n).text=v
 items=E.SubElement(t,'ItemGroup');E.SubElement(items,'PackageReference',Include='NETStandard.Library',Version='[1.6.1]');E.indent(t);E.ElementTree(t).write(folder/'Probe.csproj',encoding='utf-8',xml_declaration=True)
 r=run(tfm+'-restore',[dotnet,'restore',folder/'Probe.csproj','--configfile',out/'restore.config','-v:minimal'],required=False);assets=json.loads((folder/'obj/project.assets.json').read_text());diagnostics=assets.get('logs',[]);assert all(d['code']=='NU1101' for d in diagnostics),diagnostics
 for name in policies:
  if name+'/4.3.0' in assets['libraries']:
   package=next(p for p in feed.glob('*.nupkg') if p.name.lower()==(name+'.4.3.0.nupkg').lower());assert (out/'cache'/name.lower()/'4.3.0'/package.name.lower()).read_bytes()==package.read_bytes()
  assert not any(d.get('libraryId','').casefold()==name.casefold() for d in diagnostics)
 restores[tfm]=dict(exit_code=r.returncode,diagnostics=diagnostics,missing_IDs=sorted({d['libraryId'] for d in diagnostics}),all_candidate_packages_resolved_when_required=True)
 print(tfm,'remaining original missing package IDs:',len(restores[tfm]['missing_IDs']),flush=True)
(out/'results.json').write_text(json.dumps(dict(commands=commands,archives=archives,profiles=records,total_API_entries=sum(r['API_entries'] for r in records.values()),all_13_compile_consumers_and_original_metadata_verified=True,original_Debug_Conditional_attributes_and_Release_call_omission_verified=True,all_original_NuGet_asset_paths_aliases_and_dependency_semantics_verified=True,fresh_NETStandard161_restore_probes=restores,runtime_provider_packages_supplied=False,historical_runtime_execution_verified=False,full_dependency_goal_complete=False),indent=2)+'\n')
