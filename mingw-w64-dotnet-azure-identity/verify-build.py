"""Gate original Azure.Identity compiler inputs, source JSON reference and produced bytes."""
import os
from pathlib import Path
import hashlib,json,subprocess,sys

source,out,cache=(Path(p).resolve() for p in sys.argv[1:]);r=json.loads((out/'source-inventory.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip().replace('\\','/')
prefix=native(source)+'/'
actual={};generated={};overlays={};own=native(out)+'/'
for value in (out/'obj/Release/net8.0/compiler-inputs.txt').read_text(encoding='utf-8-sig').splitlines():
    value=value.replace('\\','/')
    if value.lower().startswith(prefix.lower()):
        relative=value[len(prefix):];assert relative in r['original_cs'];actual[relative]=sha(source/relative)
    else:
        assert value.lower().startswith(own.lower()),value
        relative=value[len(own):]
        if relative=='overlays/AuthorizationCodeCredential.cs':
            change,=r['production_cs_changes'];assert change['overlay']==relative
            data=(source/change['path']).read_bytes();assert data.count(b'            AccessToken token;')==1
            assert (out/relative).read_bytes()==data.replace(b'            AccessToken token;',b'            AccessToken token = default;')
            assert sha(out/relative)==change['prepared_sha256'];actual[change['path']]=sha(source/change['path']);overlays[change['path']]=sha(out/relative)
        else:
            assert relative in ['obj/Release/net8.0/Library.AssemblyInfo.cs','obj/Release/net8.0/.NETCoreApp,Version=v8.0.AssemblyAttributes.cs'];generated[relative]=sha(out/relative)
assert actual==r['original_cs'] and len(generated)==2
for relative,digest in r['original_project_metadata'].items():assert sha(source/relative)==digest
for relative,digest in r['original_project_tree'].items():assert sha(source/relative)==digest
for relative,digest in r['original_explicit_shared'].items():assert sha(source/relative)==digest
assert sha(source/'eng/AzureSDKClient.snk')==r['signing_key_sha256']
for relative,digest in r['prepared_project_metadata'].items():assert sha(out/relative)==digest
refs=[];dependency_refs={};cache_prefix=native(cache)+'/'
framework=Path(os.environ['MINGW_PREFIX']+'/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31');framework_prefix=native(framework)+'/'
for line in (out/'obj/Release/net8.0/reference-inputs.txt').read_text(encoding='utf-8-sig').splitlines():
    line=line.replace('\\','/')
    if line.lower().startswith(cache_prefix.lower()):
        relative=line[len(cache_prefix):];origin='source-cache';path=cache/relative
    else:
        assert line.lower().startswith(framework_prefix.lower()),line
        relative=line[len(framework_prefix):];origin='framework';path=framework/relative
    refs.append(dict(origin=origin,path=relative,sha256=sha(path)))
    if path.name in [name+'.dll' for name in r['source_dependencies']]:
        import zipfile
        name=path.stem;version=r['source_dependencies'][name]
        assert origin=='source-cache' and relative.startswith(name.lower()+'/'+version+'/'),relative
        with zipfile.ZipFile(cache/name.lower()/version/(name.lower()+'.'+version+'.nupkg')) as package:
            asset=('lib' if name=='System.Security.Cryptography.ProtectedData' else 'ref')+'/net8.0/'+name+'.dll'
            assert path.read_bytes()==package.read(asset)
        assert name not in dependency_refs
        dependency_refs[name]=relative
assert set(dependency_refs)==set(r['source_dependencies'])
r.update(actual_original_compile_items=actual,actual_overlay_compile_items=overlays,generated_sdk_metadata=generated,actual_references=refs,
 implementation_sha256=sha(out/'bin/Release/net8.0/Azure.Identity.dll'),reference_sha256=sha(out/'obj/Release/net8.0/ref/Azure.Identity.dll'),documentation_sha256=sha(out/'bin/Release/net8.0/Azure.Identity.xml'))
(out/'source-inventory.json').write_text(json.dumps(r,indent=2)+'\n')
print('PASS full132-input source inventory, exact one-line initializer overlay, two SDK metadata files, source references and library/ref/XML outputs')
