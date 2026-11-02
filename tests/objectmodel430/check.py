"""Verify the installed source package, exact assets, NuGet selection and restore gaps."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

feed,out,prefix,compiler=(Path(p).resolve() for p in sys.argv[1:]);assert not out.exists();out.mkdir()
here=Path(__file__).parent;name='System.ObjectModel';dotnet=prefix/'lib/dotnet/dotnet.exe';commands=[]
policy=json.loads((here/'inputs/published-package-policy.json').read_text())[name]
env=dict(os.environ,DOTNET_CLI_HOME=(out/'cli-home').as_posix(),NUGET_PACKAGES=(out/'cache').as_posix(),MSBuildEnableWorkloadResolver='false')
def run(label,args,required=True):
    c=[str(p) for p in args];r=subprocess.run(c,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (out/(label+'.log')).write_bytes(r.stdout);commands.append(dict(command=c,exit_code=r.returncode))
    assert not required or r.returncode==0,(label,r.stdout.decode(errors='replace')[-6000:])
    return r
package=next(p for p in feed.glob('*.nupkg') if p.name.casefold()==(name+'.4.3.0.nupkg').casefold());payload=out/'payload';payload.mkdir()
with zipfile.ZipFile(package) as z:
    expected=set(policy['reference_DLL_sha256'])|set(policy['original_data_sha256'])
    actual={n for n in z.namelist() if n.startswith(('ref/','lib/','runtimes/')) or n in policy['original_data_sha256']}
    assert actual==expected
    assert {n for n in z.namelist() if n.endswith('.dll')}==set(policy['reference_DLL_sha256'])
    for path,digest in policy['original_data_sha256'].items():assert hashlib.sha256(z.read(path)).hexdigest()==digest,path
    assert z.read('ref/netcore50/'+name+'.dll')==z.read('ref/netstandard1.3/'+name+'.dll')
    assert z.read('lib/netcore50/'+name+'.dll')!=z.read('lib/netstandard1.3/'+name+'.dll')
    for path in policy['reference_DLL_sha256']:
        p=payload/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(path))
run('all-profile-check',[sys.executable,here/'check-prototype.py',payload,out/'profiles',prefix])
(out/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
tool=out/'nuget';tool.mkdir();t=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(t,'PropertyGroup')
for n,v in dict(TargetFramework='net8.0',OutputType='Exe',UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='enable',TreatWarningsAsErrors='true',CscToolPath=(prefix/'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap').as_posix(),CscToolExe='csc50.cmd').items():E.SubElement(pg,n).text=v
ig=E.SubElement(t,'ItemGroup');E.SubElement(ig,'Compile',Include=(here/'inputs/CheckNuGet.cs').as_posix())
for n in ['NuGet.Packaging','NuGet.Frameworks','NuGet.Versioning','NuGet.Common']:E.SubElement(ig,'Reference',Include=n,HintPath=(prefix/'lib/dotnet/sdk/8.0.131'/(n+'.dll')).as_posix())
E.indent(t);E.ElementTree(t).write(tool/'NuGet.csproj',encoding='utf-8',xml_declaration=True)
run('nuget-build',[dotnet,'build',tool/'NuGet.csproj','-c','Release','--configfile',out/'NuGet.config','-p:UseSharedCompilation=false','-v:minimal'])
run('NuGet-semantics',[dotnet,tool/'bin/Release/net8.0/NuGet.dll',package,here/'inputs/published-package-policy.json'])
for path in policy['reference_DLL_sha256']:
    kind,tfm,_=path.split('/');label=kind+'-'+tfm;folder=out/label;folder.mkdir();dll=payload/path
    refs=[prefix/'lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts/System.Runtime'/('4.0.0.0' if kind=='ref' else '4.0.20.0')/'System.Runtime.dll',dll]
    args=['/nostdlib+','/target:exe','/langversion:7.3','/optimize+','/deterministic+','/warnaserror+','/nowarn:1701,1702','/out:"'+(folder/'Probe.dll').as_posix()+'"']+['/reference:"'+r.as_posix()+'"' for r in refs]+['"'+(here/'inputs/Probe.cs').as_posix()+'"']
    rsp=folder/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');run(label+'-consumer',[dotnet,compiler/'csc.dll','-noconfig','@'+str(rsp)])
    (folder/'Probe.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net8.0','framework':{'name':'Microsoft.NETCore.App','version':'8.0.31'}}})+'\n');run(label+'-consumer-run',[dotnet,folder/'Probe.dll'])
installed=(prefix/'lib/dotnet/library-packs').resolve();same=installed.as_posix().casefold()==feed.as_posix().casefold();t=E.Element('configuration');sources=E.SubElement(t,'packageSources');E.SubElement(sources,'clear');E.SubElement(sources,'add',key='candidate',value=feed.as_posix())
if not same:E.SubElement(sources,'add',key='installed',value=installed.as_posix())
mapping=E.SubElement(t,'packageSourceMapping');candidate=E.SubElement(mapping,'packageSource',key='candidate');E.SubElement(candidate,'package',pattern=name);E.SubElement(candidate if same else E.SubElement(mapping,'packageSource',key='installed'),'package',pattern='*');E.indent(t);E.ElementTree(t).write(out/'restore.config',encoding='utf-8',xml_declaration=True)
restores={}
for label,tfm,meta in [('own-ns10','netstandard1.0',False),('own-ns13','netstandard1.3',False),('own-netcore50','netcore50',False),('standard161','netstandard1.3',True)]:
    folder=out/label;folder.mkdir();t=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(t,'PropertyGroup')
    for n,v in dict(TargetFramework=tfm,EnableDefaultItems='false',DisableImplicitFrameworkReferences='true',AutomaticallyUseReferenceAssemblyPackages='false',NuGetAudit='false',TreatWarningsAsErrors='true').items():E.SubElement(pg,n).text=v
    if tfm=='netcore50':
        for n,v in dict(TargetFrameworkIdentifier='.NETCore',TargetFrameworkVersion='v5.0',UseTargetPlatformAsNuGetTargetMoniker='false',NuGetTargetMoniker='.NETCore,Version=v5.0').items():E.SubElement(pg,n).text=v
    E.SubElement(E.SubElement(t,'ItemGroup'),'PackageReference',Include='NETStandard.Library' if meta else name,Version='[1.6.1]' if meta else '[4.3.0]');E.indent(t);E.ElementTree(t).write(folder/'Probe.csproj',encoding='utf-8',xml_declaration=True)
    r=run(label+'-restore',[dotnet,'restore',folder/'Probe.csproj','--configfile',out/'restore.config','-v:minimal'],required=label=='own-ns10');assets=json.loads((folder/'obj/project.assets.json').read_text());logs=assets.get('logs',[])
    assert all(d['code']=='NU1101' for d in logs),logs
    assert not any(d.get('libraryId','').casefold()==name.casefold() for d in logs)
    if not meta:assert {d['libraryId'] for d in logs}<= {'System.Threading'},logs
    assert (out/'cache'/name.lower()/'4.3.0'/package.name.lower()).read_bytes()==package.read_bytes()
    restores[label]=dict(exit_code=r.returncode,diagnostics=logs,missing_IDs=sorted({d['libraryId'] for d in logs}))
    print(label,'restore exit',r.returncode,'remaining IDs',len(restores[label]['missing_IDs']),flush=True)
(out/'results.json').write_text(json.dumps(dict(commands=commands,profiles=json.loads((out/'profiles/results.json').read_text())['profiles'],source_NuGet_SHA256=hashlib.sha256(package.read_bytes()).hexdigest(),original_DLL_paths_verified=5,original_data_paths_verified=len(policy['original_data_sha256']),original_dependency_groups_verified=14,original_Framework_System_reference_verified=True,fresh_restores=restores,complete_parent_dependency_restore_closure=all(r['exit_code']==0 for k,r in restores.items() if k!='standard161'),NETCore50_exact_publisher_commit_verified=False,full_dependency_goal_complete=False),indent=2)+'\n')
