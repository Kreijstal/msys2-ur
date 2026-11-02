"""Check every original reference profile and exact compiler dependencies."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E

finished, private, out, prefix, compiler = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir(); here = Path(__file__).parent
dotnet = prefix / 'lib/dotnet/dotnet.exe'; commands = []
env = dict(os.environ, DOTNET_CLI_HOME=(out/'cli-home').as_posix(), MSBuildEnableWorkloadResolver='false')
def run(label, command):
    command = [str(p) for p in command]; r = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out/(label+'.log')).write_bytes(r.stdout); commands.append(dict(command=command,exit_code=r.returncode))
    assert r.returncode == 0, (label, r.stdout.decode(errors='replace')[-6000:]); return r
run('inspector-build',[sys.executable,here/'build-inspector.py',out/'inspector',prefix])
run('forwarder-build',[sys.executable,here/'build-forwarder-inspector.py',out/'forwarders',prefix])
tool=out/'resources';tool.mkdir();t=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(t,'PropertyGroup')
for n,v in dict(TargetFramework='net8.0',OutputType='Exe',AssemblyName='ReadResources',UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='disable',TreatWarningsAsErrors='true',CscToolPath=(prefix/'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap').as_posix(),CscToolExe='csc50.cmd').items():E.SubElement(pg,n).text=v
E.SubElement(E.SubElement(t,'ItemGroup'),'Compile',Include=(here/'inputs/ReadResources.cs').as_posix());E.indent(t);E.ElementTree(t).write(tool/'ReadResources.csproj',encoding='utf-8',xml_declaration=True)
(tool/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
run('resources-build',[dotnet,'build',tool/'ReadResources.csproj','-c','Release','--configfile',tool/'NuGet.config','-p:UseSharedCompilation=false','-v:minimal'])
matrix=json.loads((here/'inputs/source-contract-build-matrix.json').read_text());profiles=json.loads((here/'inputs/baselines1/profiles.json').read_text());resources=json.loads((here/'inputs/reference-data.json').read_text())
matrix['System.IO.FileSystem.Primitives/4.0.0.0']=dict(references=next(iter(json.loads((here/'inputs/FSPrimitives400.json').read_text()).values()))['references'])
matrix['System.Net.Primitives/4.0.10.0']=dict(references=json.loads((here/'inputs/source-System.Net.Primitives-4010.json').read_text())['System.Net.Primitives.dll']['references'])
symbols={'Microsoft.Win32.Primitives':'WIN32','System.Console':'CONSOLE','System.Diagnostics.Tracing':'TRACING','System.Globalization.Calendars':'CALENDARS','System.IO.FileSystem':'FILESYSTEM','System.Net.Sockets':'SOCKETS','System.Runtime.Extensions':'EXTENSIONS'}
records={};canon=lambda rows:sorted(json.dumps(r,sort_keys=True) for r in rows)
for label,row in profiles.items():
    name,tfm=row['name'],row['framework'];p=out/label;p.mkdir();dll=finished/'ref'/name/tfm/(name+'.dll')
    run(label+'-inspect',[dotnet,out/'inspector/bin/Release/net8.0/Inspect.dll',p/'metadata.json',dll]);actual=json.loads((p/'metadata.json').read_text())[name+'.dll'];expected=json.loads((here/'inputs'/(label+'.json')).read_text())[name+'.dll']
    for key in ['identity','api']:assert actual[key]==expected[key],(label,key)
    assert set(actual['references'])==set(expected['references']) and canon(actual['attributes'])==canon(expected['attributes']),label
    native=json.loads(run(label+'-resources',[dotnet,tool/'bin/Release/net8.0/ReadResources.dll',dll]).stdout)[0];want=next(r for r in resources if r['name']==name and '/'+tfm+'/' in r['file'])
    for key in ['name','version','public_key','public_key_token','attributes','resources','embedded_nonresource_blob_hashes','exported_types','native_version','references']:assert native[key]==want[key],(label,key)
    run(label+'-exports',[dotnet,out/'forwarders/bin/Release/net8.0/Forwarders.dll',p/'exports.json',dll]);exports=json.loads((p/'exports.json').read_text())[0];wanted=json.loads((here/'inputs/baselines1'/(label+'-exports.json')).read_text())[0]
    for key in ['identity','reference_only','assembly_references','exported_types']:assert exports[key]==wanted[key],(label,key)
    closure=set()
    def select(ident):
        if ident in closure:return
        closure.add(ident)
        for ref in matrix[ident]['references']:
            n,v=ref.split(', Version=');select(n+'/'+v.split(',')[0])
    for ref in actual['references']:
        n,v=ref.split(', Version=');select(n+'/'+v.split(',')[0])
    chosen={}
    for ident in closure:
        n,v=ident.split('/')
        if n not in chosen or tuple(map(int,v.split('.')))>tuple(map(int,chosen[n].split('/')[1].split('.'))):chosen[n]=ident
    refs=[private/ident/(ident.split('/')[0]+'.dll') if ident in ['System.IO.FileSystem.Primitives/4.0.0.0','System.Net.Primitives/4.0.10.0'] else prefix/'lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts'/ident/(ident.split('/')[0]+'.dll') for ident in sorted(chosen.values())]
    args=['/nostdlib+','/target:library','/optimize+','/deterministic+','/warnaserror+','/nowarn:1701,1702','/define:'+symbols[name],'/out:"'+(p/'Probe.dll').as_posix()+'"']+['/reference:"'+r.as_posix()+'"' for r in refs+[dll]]+['"'+(here/'inputs/Probe.cs').as_posix()+'"']
    rsp=p/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');run(label+'-consumer',[dotnet,compiler/'csc.dll','-noconfig','@'+str(rsp)])
    records[label]=dict(identity=actual['identity'],API_entries=len(actual['api']),DLL_sha256=hashlib.sha256(dll.read_bytes()).hexdigest(),all_original_metadata_native_resources_and_exports_equal=True,compile_consumer_passed=True)
    print('PASS original reference profile and consumer:',label,len(actual['api']),flush=True)
assert len(records)==12
(out/'results.json').write_text(json.dumps(dict(commands=commands,profiles=records,total_API_entries=sum(r['API_entries'] for r in records.values()),all_12_reference_profiles_and_consumers_passed=True,full_dependency_goal_complete=False),indent=2)+'\n')
