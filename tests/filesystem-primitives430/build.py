"""Build original reference, real enum implementation and complete Framework facade."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

sbrp,corefx,out,prefix,compiler=(Path(p).resolve() for p in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).parent;name='System.IO.FileSystem.Primitives';commands=[];sources={};profiles={}
assert hashlib.sha256(sbrp.read_bytes()).hexdigest()=='2b3136fab488246d0289e622797094e7c2eb29b35f67a9a5cd1312ef3ddfca79'
assert hashlib.sha256(corefx.read_bytes()).hexdigest()=='1782b55a84ae89baa4fcb5c8400c3d7042c5c617a4e35ce1b0ad16952d6981b2'
resources=json.loads((here/'inputs/baselines1/resource-data.json').read_text());dotnet=prefix/'lib/dotnet/dotnet.exe'
def run(label,args):
    c=[str(p) for p in args];r=subprocess.run(c,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/(label+'.log')).write_bytes(r.stdout);commands.append(dict(command=c,exit_code=r.returncode));assert r.returncode==0,(label,r.stdout.decode(errors='replace')[-6000:])
def extract(tar,entries,path,kind):
    raw=tar.extractfile(entries[path]).read();p=out/'source'/kind/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);sources[kind+'/'+path]=hashlib.sha256(raw).hexdigest();return p
with tarfile.open(sbrp) as st,tarfile.open(corefx) as ct:
    assert st.pax_headers['comment']=='5aeee2738338530a92d7f6caa2c7d5f569fed3c4' and ct.pax_headers['comment']=='4d1af962ca0fede10beb01d197367c2f90e92c97'
    se={m.name.partition('/')[2]:m for m in st if m.isfile()};ce={m.name.partition('/')[2]:m for m in ct if m.isfile()}
    extract(st,se,'LICENSE.txt','sbrp')
    for p in ['LICENSE','THIRD-PARTY-NOTICES','src/'+name+'/dir.props','src/'+name+'/src/'+name+'.csproj','src/'+name+'/src/'+name+'.builds','src/'+name+'/pkg/'+name+'.pkgproj']:extract(ct,ce,p,'corefx')
    project=E.parse(out/'source/corefx/src'/name/'src'/(name+'.csproj'));assert any(p.text=='true' for p in project.findall('.//{*}IsPartialFacadeAssembly'));assert any(p.get('Include')=='mscorlib' for p in project.findall('.//{*}TargetingPackReference'))
    assert E.parse(out/'source/corefx/src'/name/'dir.props').findtext('.//{*}AssemblyVersion')=='4.0.2.0'
    for label in ['ref-netstandard1.3','lib-netstandard1.3','ref-net46']:
        kind,tfm=label.split('-',1);folder=out/kind/tfm;folder.mkdir(parents=True);baseline=json.loads((here/'inputs/baselines1'/(label+'.json')).read_text())[name+'.dll'];identity=baseline['identity'];version=identity.split('Version=')[1].split(',')[0]
        info=['[assembly:global::System.Reflection.AssemblyVersion('+json.dumps(version)+')]']
        for row in baseline['attributes']:
            attribute=row['type']
            if attribute in ['System.Runtime.CompilerServices.CompilationRelaxationsAttribute','System.Runtime.CompilerServices.RuntimeCompatibilityAttribute','System.Diagnostics.DebuggableAttribute']:continue
            values=[v.lower() if attribute=='System.CLSCompliantAttribute' else json.dumps(v,ensure_ascii=True) for v in row['arguments']];info.append('[assembly:global::'+attribute+'('+','.join(values)+')]')
        if label=='ref-netstandard1.3':
            original=extract(st,se,'src/referencePackages/src/'+name.lower()+'/4.3.0/ref/'+tfm+'/'+name+'.cs','sbrp');text=original.read_text(encoding='utf-8-sig');projection=folder/'Declarations.cs';projection.write_text(text[text.index('namespace System.IO'):]);inputs=[projection]
            refs=[prefix/'lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts/System.Runtime/4.0.0.0/System.Runtime.dll']
        elif label=='lib-netstandard1.3':
            paths=[p.get('Include').replace('\\','/') for g in project.findall('.//{*}ItemGroup') if g.get('Condition')=="'$(TargetGroup)' != 'net46'" for p in g.findall('{*}Compile')];assert len(paths)==4
            inputs=[extract(ct,ce,'src/'+name+'/src/'+p,'corefx') for p in paths];refs=[prefix/'lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts/System.Runtime/4.0.20.0/System.Runtime.dll']
        else:
            original=extract(ct,ce,'src/'+name+'/ref/'+name+'.cs','corefx');text=original.read_text(encoding='utf-8-sig');types=re.findall(r'public enum (\w+)',text);assert types==['FileAccess','FileAttributes','FileMode','FileShare']
            exports=json.loads((here/'inputs/baselines1/ref-net46-exports.json').read_text())[0]['exported_types'];assert {'System.IO.'+t for t in types}=={r['full_name'] for r in exports};assert all(r['scope']=='mscorlib, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089' for r in exports)
            info+=['[assembly:global::System.Runtime.CompilerServices.TypeForwardedTo(typeof(global::System.IO.'+t+'))]' for t in types];inputs=[];refs=[prefix/'lib/dotnet/reference-packs/netframework46-contracts-bootstrap/ref/mscorlib.dll']
        (folder/'AssemblyInfo.cs').write_text('\n'.join(info)+'\n');inputs.append(folder/'AssemblyInfo.cs')
        v=next(r['native_version'] for r in resources if '/'+kind+'/'+tfm+'/' in r['file']);language=1033 if v['Language']=='English (United States)' else 0;assert v['Language'] in ['English (United States)','Language Neutral']
        rc=['LANGUAGE 9,1' if language else 'LANGUAGE 0,0','1 VERSIONINFO','FILEVERSION '+','.join(re.findall(r'\d+',v['FileVersion'])[:4]),'PRODUCTVERSION '+','.join(re.findall(r'\d+',v['ProductVersion'])[:4]),'FILEFLAGSMASK 0x3f','FILEFLAGS 0','FILEOS 4','FILETYPE 2','FILESUBTYPE 0','BEGIN','BLOCK "StringFileInfo"','BEGIN','BLOCK "040904b0"' if language else 'BLOCK "000004b0"','BEGIN']
        for field in ['CompanyName','FileDescription','FileVersion','InternalName','LegalCopyright','LegalTrademarks','OriginalFilename','ProductName','ProductVersion']:rc.append('VALUE '+json.dumps(field)+', L'+json.dumps(v[field],ensure_ascii=True).replace('\\u','\\x'))
        rc+=['END','END','BLOCK "VarFileInfo"','BEGIN','VALUE "Translation", '+str(language)+', 1200','END','END'];(folder/'version.rc').write_text('\n'.join(rc)+'\n');run(label+'-rc',[prefix/'bin/llvm-rc.exe','-fo',folder/'version.res',folder/'version.rc'])
        args=['/nostdlib+','/target:library','/nullable:disable','/langversion:latest','/optimize+','/deterministic+','/warnaserror+','/nowarn:1701,1702','/publicsign+','/keyfile:"'+(here/'inputs/Microsoft.snk').as_posix()+'"','/out:"'+(folder/(name+'.dll')).as_posix()+'"','/win32res:"'+(folder/'version.res').as_posix()+'"','/runtimeMetadataVersion:v4.0.30319']
        if label=='ref-netstandard1.3':args.append('/refonly')
        args+=['/reference:"'+p.as_posix()+'"' for p in refs]+['"'+p.as_posix()+'"' for p in inputs];rsp=folder/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');run(label,[dotnet,compiler/'csc.dll','-noconfig','@'+str(rsp)]);profiles[label]=dict(identity=identity,source_input_SHA256={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},reference_SHA256={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in refs});print('PASS original source profile:',label,identity,flush=True)
    target=out/'lib/net46';target.mkdir();(target/(name+'.dll')).write_bytes((out/'ref/net46'/(name+'.dll')).read_bytes())
(out/'results.json').write_text(json.dumps(dict(commands=commands,profiles=profiles,original_source_SHA256=sources,original_CoreFX_implementation_files=4,original_source_files_edited_in_place=0,original_reference_assembly_header_projection=True,original_NET46_facade_source_declaration_types=4,original_binaries_executed_or_compiler_references=False,original_Framework_runtime_execution_verified=False,full_dependency_goal_complete=False),indent=2)+'\n')
