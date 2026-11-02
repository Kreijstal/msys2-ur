"""Build complete original Framework facades, including their owned implementations."""
from pathlib import Path
import hashlib
import json
import re
import runpy
import shutil
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

archive, references, seeds, tools, out, prefix, compiler = (Path(p).resolve() for p in sys.argv[1:8])
remaining = list(sys.argv[8:])
framework462 = prefix / 'lib/dotnet/reference-packs/netframework462-contracts-bootstrap/ref'
if '--framework462' in remaining:
    index = remaining.index('--framework462'); framework462 = Path(remaining[index + 1]).resolve(); del remaining[index:index + 2]
only = set(remaining)
assert not out.exists(); out.mkdir(); here=Path(__file__).parent; dotnet=prefix/'lib/dotnet/dotnet.exe'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='1782b55a84ae89baa4fcb5c8400c3d7042c5c617a4e35ce1b0ad16952d6981b2'
profiles=json.loads((here/'inputs/profiles.json').read_text());resources=json.loads((here/'inputs/reference-data.json').read_text());commands=[];originals={};records={}
def run(label,command):
    command=[str(p) for p in command];r=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/(label+'.log')).write_bytes(r.stdout);commands.append(dict(command=command,exit_code=r.returncode));assert r.returncode==0,(label,r.stdout.decode(errors='replace')[-6000:]);return r
def extract(tar,entries,path):
    raw=tar.extractfile(entries[path]).read();p=out/'source'/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);originals[path]=hashlib.sha256(raw).hexdigest();return p
owned={'System.Diagnostics.Tracing':['System/Diagnostics/Tracing/EventCounter.cs'],'System.Net.Sockets':['System/Net/Sockets/SocketReceiveFromResult.cs','System/Net/Sockets/SocketReceiveMessageFromResult.cs','System/Net/Sockets/SocketTaskExtensions.cs']}
with tarfile.open(archive) as tar:
    assert tar.pax_headers['comment']=='4d1af962ca0fede10beb01d197367c2f90e92c97';entries={m.name.partition('/')[2]:m for m in tar if m.isfile()}
    for label,row in profiles.items():
        if row['reference_source']:continue
        if only and row['name'] not in only:continue
        name,tfm=row['name'],row['framework'];folder=out/'ref'/name/tfm;folder.mkdir(parents=True);baseline=json.loads((here/'inputs'/(label+'.json')).read_text())[name+'.dll']
        targets=[framework462/'mscorlib.dll' if tfm=='net462' else prefix/'lib/dotnet/reference-packs/netframework46-contracts-bootstrap/ref/mscorlib.dll',seeds/'System/ref/System.dll']
        assert all(p.is_file() for p in targets), 'Exact original Framework compiler contracts required'
        project=extract(tar,entries,'src/'+name+'/src/'+name+'.csproj');version=extract(tar,entries,'src/'+name+'/dir.props');package=extract(tar,entries,'src/'+name+'/pkg/'+name+'.pkgproj')
        assert any(n.text=='true' for n in E.parse(project).findall('.//{*}IsPartialFacadeAssembly'))
        assert E.parse(version).findtext('.//{*}AssemblyVersion')==baseline['identity'].split('Version=')[1].split(',')[0]
        assert any(n.findtext('{*}TargetGroup')==tfm or 'TargetGroup='+tfm in (n.findtext('{*}AdditionalProperties') or '').split(';') for n in E.parse(package).findall('.//{*}ProjectReference'))
        required={n.get('Include') for n in E.parse(project).findall('.//{*}TargetingPackReference')}
        assert 'mscorlib' in required
        contract_tfm=max((r['framework'] for r in profiles.values() if r['name']==name and r['reference_source']),key=lambda f:tuple(map(int,f.removeprefix('netstandard').split('.'))))
        contract=references/'ref'/name/contract_tfm/(name+'.dll');source=folder/'Forwards.cs'
        run(label+'-generate',[dotnet,tools/'GeneratePartialFacade/bin/Release/net8.0/GeneratePartialFacade.dll',contract,here/'inputs'/(label+'.json'),here/'inputs/baselines1'/(label+'-exports.json'),source,*targets])
        sources=[source]+[extract(tar,entries,'src/'+name+'/src/'+p) for p in owned.get(name,[])]
        source_ports=[]
        if name=='System.Net.Sockets':
            original=sources[-1];projection=folder/'SocketTaskExtensions.Net8Port.cs'
            projection.write_text(runpy.run_path(str(here/'port-socket-accept.py'))['port'](original.read_text(encoding='utf-8-sig')))
            sources[-1]=projection;source_ports.append(dict(original_source=original.as_posix(),original_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),projection_sha256=hashlib.sha256(projection.read_bytes()).hexdigest(),reason='Use matching EndAccept(out buffer, result) for BeginAccept(acceptSocket, receiveSize=0); supports Framework and NET8 receive-buffer result wrappers'))
        v=next(r for r in resources if r['name']==name and '/'+tfm+'/' in r['file']);nv=v['native_version'];assert nv['Language']=='Language Neutral'
        rc=['LANGUAGE 0,0','1 VERSIONINFO','FILEVERSION '+','.join(re.findall(r'\d+',nv['FileVersion'])[:4]),'PRODUCTVERSION '+','.join(re.findall(r'\d+',nv['ProductVersion'])[:4]),'FILEFLAGSMASK 0x3f','FILEFLAGS 0','FILEOS 4','FILETYPE 2','FILESUBTYPE 0','BEGIN','BLOCK "StringFileInfo"','BEGIN','BLOCK "000004b0"','BEGIN']
        for field in ['CompanyName','FileDescription','FileVersion','InternalName','LegalCopyright','LegalTrademarks','OriginalFilename','ProductName','ProductVersion']:rc.append('VALUE '+json.dumps(field)+', L'+json.dumps(nv[field],ensure_ascii=True).replace('\\u','\\x'))
        rc+=['END','END','BLOCK "VarFileInfo"','BEGIN','VALUE "Translation", 0, 1200','END','END'];(folder/'version.rc').write_text('\n'.join(rc)+'\n');run(label+'-rc',[prefix/'bin/llvm-rc.exe','-fo',folder/'version.res',folder/'version.rc'])
        args=['/nostdlib+','/target:library','/unsafe+','/nullable:disable','/langversion:latest','/optimize+','/deterministic+','/warnaserror+','/nowarn:1701,1702','/publicsign+','/keyfile:"'+(here/'inputs/Microsoft.snk').as_posix()+'"','/out:"'+(folder/(name+'.dll')).as_posix()+'"','/runtimeMetadataVersion:v4.0.30319','/win32res:"'+(folder/'version.res').as_posix()+'"']
        for resource,wanted in v['resources'].items():
            resx=extract(tar,entries,'src/'+name+'/src/Resources/Strings.resx');values={n.get('name'):n.findtext('value') for n in E.parse(resx).findall('data')};assert values==wanted,(name,'original resource values')
            result=folder/resource;run(label+'-resources',[dotnet,tools/'WriteResources/bin/Release/net8.0/WriteResources.dll',resx,result]);args.append('/resource:"'+result.as_posix()+'",'+resource)
        args+=['/reference:"'+p.as_posix()+'"' for p in targets]+['"'+p.as_posix()+'"' for p in sources];rsp=folder/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');run(label+'-compile',[dotnet,compiler/'csc.dll','-noconfig','@'+str(rsp)])
        if name=='System.Runtime.Extensions':
            raw=folder/'raw';raw.mkdir();shutil.move(folder/(name+'.dll'),raw/(name+'.dll'))
            run(label+'-original-export-set',[dotnet,tools/'PortExtensionExports/bin/Release/net8.0/PortExtensionExports.dll',raw/(name+'.dll'),here/'inputs/baselines1'/(label+'-exports.json'),folder/(name+'.dll')])
        records[label]=dict(identity=baseline['identity'],source_files={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},original_source_owned_implementation_files=len(sources)-1,explicit_source_ports=source_ports,source_resource_strings=sum(len(v) for v in v['resources'].values()),source_Framework_reference_hashes={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in targets})
        print('PASS original source partial facade:',label,'owned source files',len(sources)-1,flush=True)
assert len(records)==(len(only) if only else 7)
(out/'results.json').write_text(json.dumps(dict(commands=commands,facades=records,original_CoreFX_source_sha256=originals,original_source_files_edited_in_place=0,explicit_owned_source_projections=sum(len(r['explicit_source_ports']) for r in records.values()),original_resources_generated_from_source=True,source_reference_declarations_and_Framework_forwarding_scopes_verified=True,original_Framework_runtime_or_upstream_workflow_replayed=False,publisher_binaries_executed_or_compiler_inputs=False,full_dependency_goal_complete=False),indent=2)+'\n')
