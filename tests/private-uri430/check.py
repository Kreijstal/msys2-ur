"""Verify original carrier assets and source-only restore without provider substitution."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

feed,out,prefix=(Path(p).resolve() for p in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).parent;policy=json.loads((here/'inputs/policy.json').read_text())
package=next(p for p in feed.glob('*.nupkg') if p.name.casefold()=='system.private.uri.4.3.0.nupkg')
with zipfile.ZipFile(package) as z:
    assert not any(p.endswith(('.dll','.exe')) for p in z.namelist())
    data={p for p in z.namelist() if p.startswith(('lib/','ref/','runtimes/')) or p in policy['original_data_SHA256']};assert data==set(policy['original_data_SHA256'])
    for p,digest in policy['original_data_SHA256'].items():assert hashlib.sha256(z.read(p)).hexdigest()==digest
    t=E.fromstring(z.read(next(p for p in z.namelist() if p.endswith('.nuspec'))));meta=t.find('{*}metadata')
    assert meta.findtext('{*}id')==policy['package'] and meta.findtext('{*}version')==policy['version']
    assert {e.get('id'):e.get('version') for e in meta.findall('{*}dependencies/{*}dependency')}==policy['original_dependencies']
installed=prefix/'lib/dotnet/library-packs';sources=[feed] if feed.as_posix().casefold()==installed.as_posix().casefold() else [feed,installed]
t=E.Element('configuration');ps=E.SubElement(t,'packageSources');E.SubElement(ps,'clear')
for n,p in enumerate(sources):E.SubElement(ps,'add',key='source'+str(n),value=p.as_posix())
E.indent(t);E.ElementTree(t).write(out/'NuGet.config',encoding='utf-8',xml_declaration=True)
env=dict(os.environ,DOTNET_CLI_HOME=(out/'cli-home').as_posix(),NUGET_PACKAGES=(out/'cache').as_posix(),MSBuildEnableWorkloadResolver='false');checks=[]
for tfm in ['netstandard1.3','netcore50']:
    folder=out/tfm;folder.mkdir();t=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(t,'PropertyGroup')
    for k,v in dict(TargetFramework=tfm,DisableImplicitFrameworkReferences='true',EnableDefaultItems='false',AutomaticallyUseReferenceAssemblyPackages='false',NuGetAudit='false',TreatWarningsAsErrors='true').items():E.SubElement(pg,k).text=v
    if tfm=='netcore50':
        for k,v in dict(TargetFrameworkIdentifier='.NETCore',TargetFrameworkVersion='v5.0',UseTargetPlatformAsNuGetTargetMoniker='false',NuGetTargetMoniker='.NETCore,Version=v5.0',RuntimeIdentifier='aot').items():E.SubElement(pg,k).text=v
    E.SubElement(E.SubElement(t,'ItemGroup'),'PackageReference',Include=policy['package'],Version='[4.3.0]');E.indent(t);E.ElementTree(t).write(folder/'Probe.csproj',encoding='utf-8',xml_declaration=True)
    cmd=[str(prefix/'lib/dotnet/dotnet.exe'),'restore',str(folder/'Probe.csproj'),'--configfile',str(out/'NuGet.config'),'-v:minimal'];r=subprocess.run(cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/(tfm+'.log')).write_bytes(r.stdout);assert r.returncode==0,r.stdout.decode(errors='replace')[-5000:]
    assert (out/'cache/system.private.uri/4.3.0/system.private.uri.4.3.0.nupkg').read_bytes()==package.read_bytes()
    assets=json.loads((folder/'obj/project.assets.json').read_text());assert not assets.get('logs',[])
    for target in assets['targets'].values():
        row=target['System.Private.Uri/4.3.0'];assert not any(p.endswith('.dll') for key in ['compile','runtime','runtimeTargets'] for p in row.get(key,{}))
    checks.append(dict(framework=tfm,command=cmd,exit_code=r.returncode))
(out/'results.json').write_text(json.dumps(dict(checks=checks,source_NuGet_SHA256=hashlib.sha256(package.read_bytes()).hexdigest(),all_original_data_and_dependencies_verified=True,original_DLL_count=0,runtime_implementation_not_claimed=True,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS exact original metadata/data/dependencies and two fresh source-only restores')
