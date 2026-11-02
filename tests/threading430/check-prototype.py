"""Compare source builds to frozen original metadata and execute both runtimes."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E

build,aot,corelib,compiler,out,prefix=(Path(p).resolve() for p in sys.argv[1:])
assert not out.exists();out.mkdir()
here=Path(__file__).parent;name='System.Threading';commands=[]
dotnet=prefix/'lib/dotnet/dotnet.exe'
env=dict(os.environ,DOTNET_CLI_HOME=(out/'cli-home').as_posix(),NUGET_PACKAGES=(out/'cache').as_posix(),MSBuildEnableWorkloadResolver='false')
def run(label,args):
    c=[str(p) for p in args];r=subprocess.run(c,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (out/(label+'.log')).write_bytes(r.stdout);commands.append(dict(command=c,exit_code=r.returncode))
    assert r.returncode==0,(label,r.stdout.decode(errors='replace')[-6000:])
    return r
def tool(label,source):
    folder=out/label;folder.mkdir();t=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(t,'PropertyGroup')
    for n,v in dict(TargetFramework='net8.0',OutputType='Exe',UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='disable' if label=='ReadResources' else 'enable',TreatWarningsAsErrors='true',CscToolPath=(prefix/'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap').as_posix(),CscToolExe='csc50.cmd').items():E.SubElement(pg,n).text=v
    E.SubElement(E.SubElement(t,'ItemGroup'),'Compile',Include=(here/'inputs'/source).as_posix());E.indent(t);E.ElementTree(t).write(folder/(label+'.csproj'),encoding='utf-8',xml_declaration=True)
    run(label+'-build',[dotnet,'build',folder/(label+'.csproj'),'-c','Release','--configfile',out/'NuGet.config','-p:UseSharedCompilation=false','-v:minimal'])
    return folder/'bin/Release/net8.0'/(label+'.dll')
(out/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
run('inspector-build',[sys.executable,here/'build-inspector.py',out/'inspector',prefix])
run('forwarder-build',[sys.executable,here/'build-forwarder-inspector.py',out/'forwarders',prefix])
reader=tool('ReadResources','ReadResources.cs');host=tool('Host','Host.cs')
resources=json.loads((here/'inputs/baselines1/resource-data.json').read_text());records={}
canon=lambda rows:sorted(json.dumps(r,sort_keys=True) for r in rows)
for label in ['ref-netstandard1.0','ref-netstandard1.3','ref-netcore50','lib-netcore50','runtimes-aot-lib-netcore50','lib-netstandard1.3']:
    kind,tfm=label.split('-',1);dll=aot/'runtimes/aot/lib/netcore50'/(name+'.dll') if kind=='runtimes' else build/kind/tfm/(name+'.dll')
    folder=out/label;folder.mkdir()
    run(label+'-metadata',[dotnet,out/'inspector/bin/Release/net8.0/Inspect.dll',folder/'metadata.json',dll])
    got=json.loads((folder/'metadata.json').read_text())[name+'.dll'];want=json.loads((here/'inputs/baselines1'/(label+'.json')).read_text())[name+'.dll']
    for key in ['identity','api']:assert got[key]==want[key],(label,key)
    assert set(got['references'])==set(want['references']),(label,'references',got['references'])
    assert canon(got['attributes'])==canon(want['attributes']),(label,'attributes',got['attributes'])
    actual=json.loads(run(label+'-resources',[dotnet,reader,dll]).stdout)[0];expected=next(r for r in resources if ('/runtimes/aot/lib/netcore50/' if kind=='runtimes' else '/'+kind+'/'+tfm+'/') in r['file'])
    for key in ['name','version','public_key','public_key_token','attributes','resources','embedded_nonresource_blob_hashes','exported_types','native_version','references']:assert actual[key]==expected[key],(label,key)
    run(label+'-exports',[dotnet,out/'forwarders/bin/Release/net8.0/Forwarders.dll',folder/'exports.json',dll])
    a=json.loads((folder/'exports.json').read_text())[0];b=json.loads((here/'inputs/baselines1'/(label+'-exports.json')).read_text())[0]
    for key in ['identity','reference_only','assembly_references','exported_types']:assert a[key]==b[key],(label,key)
    records[label]=dict(identity=got['identity'],API_entries=len(got['api']),SHA256=hashlib.sha256(dll.read_bytes()).hexdigest(),all_original_metadata_resources_scopes_exports_verified=True)
    print('PASS strict original metadata:',label,flush=True)
    if label!='lib-netstandard1.3':continue
    args=['/nostdlib+','/target:exe','/nullable:enable','/langversion:latest','/optimize+','/deterministic+','/warnaserror+','/reference:"'+corelib.as_posix()+'"','/reference:candidate="'+dll.as_posix()+'"','/out:"'+(folder/'Run.dll').as_posix()+'"','"'+(here/'inputs/Run.cs').as_posix()+'"']
    rsp=folder/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');run(label+'-runner-build',[dotnet,compiler/'csc.dll','-noconfig','@'+str(rsp)])
    run(label+'-runtime',[dotnet,host,folder/'Run.dll',dll])
    records[label]['actual_candidate_runtime_checks_passed']=True
    print('PASS actual candidate runtime:',label,flush=True)
(out/'results.json').write_text(json.dumps(dict(commands=commands,profiles=records,AOT_private_provider_runtime_execution_verified=False,source_build=json.loads((build/'results.json').read_text()) if (build/'results.json').exists() else None,all_original_six_asset_paths_verified=True,full_parent_package_installed=False,full_dependency_goal_complete=False),indent=2)+'\n')
