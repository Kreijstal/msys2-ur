"""Validate complete parent NuGets, all original profiles and remaining real gaps."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

feed,private,out,prefix,compiler=(Path(p).resolve() for p in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).parent;dotnet=prefix/'lib/dotnet/dotnet.exe';commands=[]
env=dict(os.environ,DOTNET_CLI_HOME=(out/'cli-home').as_posix(),NUGET_PACKAGES=(out/'cache').as_posix(),MSBuildEnableWorkloadResolver='false')
def run(label,command,required=True):
    command=[str(p) for p in command];r=subprocess.run(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/(label+'.log')).write_bytes(r.stdout);commands.append(dict(command=command,exit_code=r.returncode));assert not required or r.returncode==0,(label,r.stdout.decode(errors='replace')[-6000:]);return r
policies=json.loads((here/'inputs/published-package-policy.json').read_text());archives={};payload=out/'payload'
for name,policy in policies.items():
    package=next(p for p in feed.glob('*.nupkg') if p.name.casefold()==(name+'.4.3.0.nupkg').casefold())
    with zipfile.ZipFile(package) as z:
        expected=set(policy['reference_DLL_sha256'])|set(policy['original_data_sha256']);actual={n for n in z.namelist() if n.startswith(('ref/','lib/','runtimes/')) or n in policy['original_data_sha256']};assert actual==expected,(name,actual^expected)
        assert {n for n in z.namelist() if n.endswith('.dll')}==set(policy['reference_DLL_sha256']);assert not any(n.endswith('.exe') for n in z.namelist())
        for path,digest in policy['original_data_sha256'].items():assert hashlib.sha256(z.read(path)).hexdigest()==digest,path
        by_hash={}
        for path,digest in policy['reference_DLL_sha256'].items():by_hash.setdefault(digest,[]).append(path)
        for group in by_hash.values():assert all(z.read(n)==z.read(group[0]) for n in group),group
        for path in policy['reference_DLL_sha256']:
            if '/netcore50/' in path:continue
            tfm=path.split('/')[1];target=payload/'ref'/name/tfm/(name+'.dll');target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():assert target.read_bytes()==z.read(path)
            else:target.write_bytes(z.read(path))
        archives[name]=dict(sha256=hashlib.sha256(package.read_bytes()).hexdigest(),DLL_asset_paths=len(policy['reference_DLL_sha256']),framework_markers=sum(p.endswith('_._') for p in policy['original_data_sha256']),original_data_and_alias_bytes_verified=True)
run('references',[sys.executable,here/'check-references.py',payload,private,out/'references',prefix,compiler])
run('facades',[sys.executable,here/'check-facades.py',payload,out/'facades',out/'references',prefix])
run('runtime',[sys.executable,here/'run-facades.py',payload,out/'runtime',prefix])
t=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(t,'PropertyGroup')
for n,v in dict(TargetFramework='net8.0',OutputType='Exe',AssemblyName='CheckNuGet',UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='enable',TreatWarningsAsErrors='true',CscToolPath=(prefix/'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap').as_posix(),CscToolExe='csc50.cmd').items():E.SubElement(pg,n).text=v
ig=E.SubElement(t,'ItemGroup');E.SubElement(ig,'Compile',Include=(here/'inputs/CheckNuGet.cs').as_posix())
for n in ['NuGet.Packaging','NuGet.Frameworks','NuGet.Versioning','NuGet.Common']:E.SubElement(ig,'Reference',Include=n,HintPath=(prefix/'lib/dotnet/sdk/8.0.131'/(n+'.dll')).as_posix())
E.indent(t);E.ElementTree(t).write(out/'CheckNuGet.csproj',encoding='utf-8',xml_declaration=True);(out/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
run('NuGet-tool',[dotnet,'build',out/'CheckNuGet.csproj','-c','Release','--configfile',out/'NuGet.config','-p:UseSharedCompilation=false','-v:minimal'])
for name in policies:
    package=next(p for p in feed.glob('*.nupkg') if p.name.casefold()==(name+'.4.3.0.nupkg').casefold());run(name+'-semantics',[dotnet,out/'bin/Release/net8.0/CheckNuGet.dll',package,here/'inputs/published-package-policy.json'])
installed=(prefix/'lib/dotnet/library-packs').resolve();same=installed.as_posix().casefold()==feed.as_posix().casefold();t=E.Element('configuration');sources=E.SubElement(t,'packageSources');E.SubElement(sources,'clear');E.SubElement(sources,'add',key='candidate',value=feed.as_posix())
if not same:E.SubElement(sources,'add',key='installed',value=installed.as_posix())
mapping=E.SubElement(t,'packageSourceMapping');candidate=E.SubElement(mapping,'packageSource',key='candidate')
for name in policies:E.SubElement(candidate,'package',pattern=name)
E.SubElement(candidate if same else E.SubElement(mapping,'packageSource',key='installed'),'package',pattern='*');E.indent(t);E.ElementTree(t).write(out/'restore.config',encoding='utf-8',xml_declaration=True)
restores={}
for tfm in ['netstandard1.0','netstandard1.3']:
    folder=out/('restore-'+tfm);folder.mkdir();t=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(t,'PropertyGroup')
    for n,v in dict(TargetFramework=tfm,EnableDefaultItems='false',DisableImplicitFrameworkReferences='true',NuGetAudit='false',TreatWarningsAsErrors='true').items():E.SubElement(pg,n).text=v
    E.SubElement(E.SubElement(t,'ItemGroup'),'PackageReference',Include='NETStandard.Library',Version='[1.6.1]');E.indent(t);E.ElementTree(t).write(folder/'Probe.csproj',encoding='utf-8',xml_declaration=True)
    r=run(tfm+'-restore',[dotnet,'restore',folder/'Probe.csproj','--configfile',out/'restore.config','-v:minimal'],required=False);assets=json.loads((folder/'obj/project.assets.json').read_text());diagnostics=assets.get('logs',[]);assert all(d['code']=='NU1101' for d in diagnostics),diagnostics
    for name in policies:
        if name+'/4.3.0' in assets['libraries']:
            package=next(p for p in feed.glob('*.nupkg') if p.name.casefold()==(name+'.4.3.0.nupkg').casefold());assert (out/'cache'/name.lower()/'4.3.0'/package.name.lower()).read_bytes()==package.read_bytes()
        assert not any(d.get('libraryId','').casefold()==name.casefold() for d in diagnostics)
    restores[tfm]=dict(exit_code=r.returncode,diagnostics=diagnostics,missing_IDs=sorted({d['libraryId'] for d in diagnostics}),candidate_source_archive_bytes_verified_when_required=True)
    print(tfm,'remaining original missing IDs:',len(restores[tfm]['missing_IDs']),flush=True)
refs=json.loads((out/'references/results.json').read_text());facades=json.loads((out/'facades/results.json').read_text());runtime=json.loads((out/'runtime/results.json').read_text())
(out/'results.json').write_text(json.dumps(dict(commands=commands,archives=archives,reference_profiles=refs['profiles'],reference_API_entries=refs['total_API_entries'],facades=facades['facades'],owned_API_entries=facades['original_owned_API_entries'],original_exported_records=facades['original_exported_types'],original_source_resource_strings=facades['original_source_resource_strings'],runtime_execution=runtime,all_original_assets_aliases_data_and_NuGet_framework_dependency_semantics_verified=True,fresh_NETStandard161_restore_probes=restores,runtime_any_AOT_providers_supplied=False,original_Framework_runtime_execution_verified=False,full_dependency_goal_complete=False),indent=2)+'\n')
