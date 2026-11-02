"""Build the original ObjectModel reference and two historical runtime implementations."""
from pathlib import Path
import hashlib
import json
import re
import runpy
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

sbrp,corefx,corefx2015,out,prefix,compiler=(Path(p).resolve() for p in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).parent;name='System.ObjectModel';commands=[];originals={};profiles={};dotnet=prefix/'lib/dotnet/dotnet.exe'
assert hashlib.sha256(sbrp.read_bytes()).hexdigest()=='2b3136fab488246d0289e622797094e7c2eb29b35f67a9a5cd1312ef3ddfca79'
assert hashlib.sha256(corefx.read_bytes()).hexdigest()=='1782b55a84ae89baa4fcb5c8400c3d7042c5c617a4e35ce1b0ad16952d6981b2'
assert hashlib.sha256(corefx2015.read_bytes()).hexdigest()=='3c8ec58eccf0a83ba38d65d3ae6dbff7ca9be8fa5a4447c935f3ede9a1946b36'
provenance=json.loads((here/'inputs/original-profile-provenance.json').read_text());assert provenance['ref_NETCore50_NS13_byte_identical'] and not provenance['lib_NETCore50_NS13_byte_identical']
resources=json.loads((here/'inputs/baselines1/resource-data.json').read_text());matrix=json.loads((here/'inputs/source-contract-build-matrix.json').read_text())
def run(label,args):
    c=[str(p) for p in args];r=subprocess.run(c,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/(label+'.log')).write_bytes(r.stdout);commands.append(dict(command=c,exit_code=r.returncode));assert r.returncode==0,(label,r.stdout.decode(errors='replace')[-6000:])
def extract(tar,entries,path,kind):
    raw=tar.extractfile(entries[path]).read();p=out/'source'/kind/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);originals[kind+'/'+path]=hashlib.sha256(raw).hexdigest();return p
tool=out/'resources-tool';tool.mkdir();t=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(t,'PropertyGroup')
for n,v in dict(TargetFramework='net8.0',OutputType='Exe',UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='enable',TreatWarningsAsErrors='true',CscToolPath=(prefix/'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap').as_posix(),CscToolExe='csc50.cmd').items():E.SubElement(pg,n).text=v
E.SubElement(E.SubElement(t,'ItemGroup'),'Compile',Include=(here/'inputs/WriteResources.cs').as_posix());E.indent(t);E.ElementTree(t).write(tool/'Resources.csproj',encoding='utf-8',xml_declaration=True);(tool/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n');run('resources-tool-build',[dotnet,'build',tool/'Resources.csproj','-c','Release','--configfile',tool/'NuGet.config','-p:UseSharedCompilation=false','-v:minimal'])
with tarfile.open(sbrp) as st,tarfile.open(corefx) as ct,tarfile.open(corefx2015) as old:
    assert st.pax_headers['comment']=='5aeee2738338530a92d7f6caa2c7d5f569fed3c4' and ct.pax_headers['comment']=='4d1af962ca0fede10beb01d197367c2f90e92c97';se={m.name.partition('/')[2]:m for m in st if m.isfile()};ce={m.name.partition('/')[2]:m for m in ct if m.isfile()}
    extract(st,se,'LICENSE.txt','sbrp')
    for p in ['LICENSE','THIRD-PARTY-NOTICES','src/'+name+'/dir.props','src/'+name+'/src/'+name+'.csproj','src/'+name+'/src/project.json','src/'+name+'/pkg/'+name+'.pkgproj']:extract(ct,ce,p,'corefx')
    oe={m.name.partition('/')[2]:m for m in old if m.isfile()};assert old.pax_headers['comment']=='f63d0119fcdd5a9232f38efdf7ceb957b94d6a40'
    project=E.parse(out/'source/corefx/src'/name/'src'/(name+'.csproj'));assert E.parse(out/'source/corefx/src'/name/'dir.props').findtext('.//{*}AssemblyVersion')=='4.0.13.0'
    for label in ['ref-netstandard1.0','ref-netstandard1.3','lib-netcore50','lib-netstandard1.3']:
        kind,tfm=label.split('-',1);folder=out/kind/tfm;folder.mkdir(parents=True);baseline=json.loads((here/'inputs/baselines1'/(label+'.json')).read_text())[name+'.dll'];version=baseline['identity'].split('Version=')[1].split(',')[0];info=['[assembly:global::System.Reflection.AssemblyVersion('+json.dumps(version)+')]']
        for row in baseline['attributes']:
            attr=row['type']
            if attr in ['System.Runtime.CompilerServices.CompilationRelaxationsAttribute','System.Runtime.CompilerServices.RuntimeCompatibilityAttribute','System.Diagnostics.DebuggableAttribute','System.Reflection.AssemblyKeyFileAttribute','System.Reflection.AssemblyDelaySignAttribute']:continue
            info.append('[assembly:global::'+attr+'('+','.join(v.lower() if attr=='System.CLSCompliantAttribute' else json.dumps(v,ensure_ascii=True) for v in row['arguments'])+')]')
        closure=set()
        def select(ident):
            if ident in closure:return
            assert ident in matrix,ident
            closure.add(ident)
            for ref in matrix[ident]['references']:
                n,v=ref.split(', Version=');select(n+'/'+v.split(',')[0])
        for ref in baseline['references']:
            n,v=ref.split(', Version=');select(n+'/'+v.split(',')[0])
        inputs=[];extra=[]
        if kind=='ref':
            source=extract(st,se,'src/referencePackages/src/'+name.lower()+'/4.3.0/ref/'+tfm+'/'+name+'.cs','sbrp');text=source.read_text(encoding='utf-8-sig');projection=folder/'Declarations.cs';projection.write_text(runpy.run_path(str(here/'port-additional.py'))['object_model'](text[text.index('namespace System.Collections'):]) if tfm=='netstandard1.0' else text[text.index('namespace System.Collections') :]);inputs=[projection]
        else:
            source_tar,source_entries,source_kind=(old,oe,'corefx2015') if tfm=='netcore50' else (ct,ce,'corefx')
            runtime_project=E.fromstring(source_tar.extractfile(source_entries['src/'+name+'/src/'+name+'.csproj']).read())
            extract(source_tar,source_entries,'src/'+name+'/src/'+name+'.csproj',source_kind)
            for license_path in ['LICENSE','THIRD-PARTY-NOTICES']:
                if license_path in source_entries:extract(source_tar,source_entries,license_path,source_kind)
            dependencies=json.loads((out/'source/corefx/src'/name/'src/project.json').read_text())['frameworks']['netstandard1.3']['dependencies']
            for n,v in dependencies.items():
                if n.startswith('System.'):select(n+'/'+v+'.0' if v.count('.')==2 else n+'/'+v)
            for group in runtime_project.findall('.//{*}ItemGroup'):
                if tfm!='netcore50' and group.get('Condition')!="'$(TargetGroup)' != 'net46'":continue
                for node in group.findall('{*}Compile'):
                    p=node.get('Include').replace('\\','/');p=p.replace('$(CommonPath)/','src/Common/src/') if p.startswith('$(CommonPath)') else 'src/'+name+'/src/'+p;inputs.append(extract(source_tar,source_entries,p,source_kind))
            assert len(inputs)==16
            inputs.append(extract(source_tar,source_entries,'src/Common/src/System/SR.cs',source_kind))
            resx=extract(source_tar,source_entries,'src/'+name+'/src/Resources/Strings.resx',source_kind);values={n.get('name'):n.findtext('value') for n in E.parse(resx).findall('data')};original=next(r['resources'] for r in resources if '/lib/'+tfm+'/' in r['file']);assert len(original)==1 and values==next(iter(original.values()))
            logical=next(iter(original));resource=folder/logical;run('resources',[dotnet,tool/'bin/Release/net8.0/Resources.dll',resx,resource]);extra.append('/resource:"'+resource.as_posix()+'",'+logical)
            code=['namespace FxResources.System.ObjectModel {internal static class SR {}}','namespace System {internal partial class SR {private static System.Type ResourceType {get {return typeof(FxResources.System.ObjectModel.SR);}}']+['internal static string @'+n+' {get {return GetResourceString('+json.dumps(n)+',null);}}' for n in values]+['}}'];generated=folder/'SR.Generated.cs';generated.write_text('\n'.join(code)+'\n');inputs.append(generated)
        chosen={}
        for ident in closure:
            n,v=ident.split('/')
            if n not in chosen or tuple(map(int,v.split('.')))>tuple(map(int,chosen[n].split('/')[1].split('.'))):chosen[n]=ident
        refs=[prefix/'lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts'/ident/(ident.split('/')[0]+'.dll') for ident in sorted(chosen.values())];assert all(p.is_file() for p in refs)
        (folder/'AssemblyInfo.cs').write_text('\n'.join(info)+'\n');inputs.append(folder/'AssemblyInfo.cs');nv=next(r['native_version'] for r in resources if '/'+kind+'/'+tfm+'/' in r['file']);assert nv['Language']=='Language Neutral'
        rc=['LANGUAGE 0,0','1 VERSIONINFO','FILEVERSION '+','.join(re.findall(r'\d+',nv['FileVersion'])[:4]),'PRODUCTVERSION '+','.join(re.findall(r'\d+',nv['ProductVersion'])[:4]),'FILEFLAGSMASK 0x3f','FILEFLAGS 0','FILEOS 4','FILETYPE 2','FILESUBTYPE 0','BEGIN','BLOCK "StringFileInfo"','BEGIN','BLOCK "000004b0"','BEGIN']
        for field in ['CompanyName','FileDescription','FileVersion','InternalName','LegalCopyright','LegalTrademarks','OriginalFilename','ProductName','ProductVersion']:rc.append('VALUE '+json.dumps(field)+', L'+json.dumps(nv[field],ensure_ascii=True).replace('\\u','\\x'))
        rc+=['END','END','BLOCK "VarFileInfo"','BEGIN','VALUE "Translation", 0, 1200','END','END'];(folder/'version.rc').write_text('\n'.join(rc)+'\n');run(label+'-rc',[prefix/'bin/llvm-rc.exe','-fo',folder/'version.res',folder/'version.rc'])
        args=['/nostdlib+','/target:library','/unsafe+','/nullable:disable','/langversion:latest','/optimize+','/deterministic+','/warnaserror+','/nowarn:1701,1702','/publicsign+','/keyfile:"'+(here/'inputs/Microsoft.snk').as_posix()+'"','/out:"'+(folder/(name+'.dll')).as_posix()+'"','/win32res:"'+(folder/'version.res').as_posix()+'"','/runtimeMetadataVersion:v4.0.30319']+extra
        if kind=='ref':args.append('/refonly')
        args+=['/reference:"'+r.as_posix()+'"' for r in refs]+['"'+p.as_posix()+'"' for p in inputs];rsp=folder/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');run(label,[dotnet,compiler/'csc.dll','-noconfig','@'+str(rsp)]);profiles[label]=dict(identity=baseline['identity'],source_input_SHA256={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},reference_SHA256={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in refs});print('PASS source ObjectModel profile:',label,flush=True)
    run('attribute-restorer-build',[sys.executable,here/'build-attribute-restorer.py',out/'attribute-restorer',prefix])
    raw=out/'ref/netstandard1.0'/(name+'.dll');restored=raw.with_suffix('.restored.dll')
    run('restore-original-NS10-signing-metadata',[dotnet,out/'attribute-restorer/bin/Release/net8.0/RestoreAttributes.dll',here/'inputs/baselines1/ref-netstandard1.0.json',raw,restored]);restored.replace(raw)
    folder=out/'ref/netcore50';folder.mkdir();(folder/(name+'.dll')).write_bytes((out/'ref/netstandard1.3'/(name+'.dll')).read_bytes())
(out/'results.json').write_text(json.dumps(dict(commands=commands,profiles=profiles,original_source_SHA256=originals,original_project_implementation_files_per_runtime=16,source_resource_strings_per_runtime=15,original_source_files_edited_in_place=0,original_reference_header_projection=True,restored_NS10_Synchronized_interface_event_accessors=8,NETCore50_source_commit='f63d0119fcdd5a9232f38efdf7ceb957b94d6a40',NETCore50_exact_publisher_commit_verified=False,NETCore50_source_reconstruction=True,NS13_exact_original_source_commit_verified=True,original_binaries_executed_or_compiler_inputs=False,full_dependency_goal_complete=False),indent=2)+'\n')
