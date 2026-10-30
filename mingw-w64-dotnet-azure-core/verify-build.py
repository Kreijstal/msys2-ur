"""Gate original Azure.Core compiler inputs, source JSON reference and produced bytes."""
import os
from pathlib import Path
import hashlib,json,subprocess,sys

source,out,cache=(Path(p).resolve() for p in sys.argv[1:]);r=json.loads((out/'source-inventory.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip().replace('\\','/')
prefix=native(source)+'/'
actual={};generated={};own=native(out)+'/'
for value in (out/'obj/Release/net8.0/compiler-inputs.txt').read_text(encoding='utf-8-sig').splitlines():
    value=value.replace('\\','/')
    if value.lower().startswith(prefix.lower()):
        relative=value[len(prefix):];assert relative in r['original_cs'];actual[relative]=sha(source/relative)
    else:
        assert value.lower().startswith(own.lower()),value
        relative=value[len(own):];assert relative in ['obj/Release/net8.0/Library.AssemblyInfo.cs','obj/Release/net8.0/.NETCoreApp,Version=v8.0.AssemblyAttributes.cs'];generated[relative]=sha(out/relative)
assert actual==r['original_cs'] and len(generated)==2
for relative,digest in r['original_project_metadata'].items():assert sha(source/relative)==digest
for relative,digest in r['original_project_tree'].items():assert sha(source/relative)==digest
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
            assert path.read_bytes()==package.read('ref/net8.0/'+name+'.dll')
        assert name not in dependency_refs
        dependency_refs[name]=relative
assert set(dependency_refs)==set(r['source_dependencies'])
generated_json={p.relative_to(out).as_posix():sha(p) for p in (out/'obj/Release/net8.0/generated').rglob('*.cs')}
assert generated_json
generators=[]
for value in (out/'obj/Release/net8.0/analyzer-inputs.txt').read_text(encoding='utf-8-sig').splitlines():
    value=value.replace('\\','/')
    if not value.endswith('/System.Text.Json.SourceGeneration.dll'):continue
    assert value.lower().startswith(cache_prefix.lower()),value
    relative=value[len(cache_prefix):]
    assert relative=='system.text.json/8.0.5/analyzers/dotnet/roslyn4.4/cs/System.Text.Json.SourceGeneration.dll'
    with zipfile.ZipFile(cache/'system.text.json/8.0.5/system.text.json.8.0.5.nupkg') as package:
        assert (cache/relative).read_bytes()==package.read(relative.split('/8.0.5/',1)[1])
    generators.append(dict(path=relative,sha256=sha(cache/relative)))
assert len(generators)==1
r.update(json_source_generators=generators,json_generated_files=generated_json,actual_original_compile_items=actual,generated_sdk_metadata=generated,actual_references=refs,
 implementation_sha256=sha(out/'bin/Release/net8.0/Azure.Core.dll'),reference_sha256=sha(out/'obj/Release/net8.0/ref/Azure.Core.dll'),documentation_sha256=sha(out/'bin/Release/net8.0/Azure.Core.xml'))
(out/'source-inventory.json').write_text(json.dumps(r,indent=2)+'\n')
print('PASS all193 original compiler items, two SDK metadata files, exact source dependency references and library/ref/XML outputs')
