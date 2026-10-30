"""Gate actual .NET8 library/generator compiler inputs against original source."""
import os
from pathlib import Path
import hashlib,json,subprocess,sys

source,prepared,cache=(Path(p).resolve() for p in sys.argv[1:])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip().replace('\\','/')
source_prefix=native(source)+'/'
records=json.loads((prepared/'source-inventory.json').read_text())
roots=[('source-cache',cache),('framework',Path(os.environ['MINGW_PREFIX']+'/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31'))]
roots=[(label,path,native(path)+'/') for label,path in roots]
total=0
for folder,record in records.items():
    target=prepared/folder;prefix=native(target)+'/'
    expected=record['expected_original_compile_items'];actual={};generated={}
    for relative,digest in expected.items():assert sha(source/relative)==digest,relative
    for relative,digest in record['original_project_metadata'].items():assert sha(source/relative)==digest,relative
    for relative,digest in record['original_resource_sources'].items():assert sha(source/relative)==digest,relative
    values=(target/'obj/Release/net8.0/compiler-inputs.txt').read_text(encoding='utf-8-sig').splitlines()
    assert len(values)==len(set(values)),folder
    for value in values:
        value=value.replace('\\','/')
        if value.lower().startswith(source_prefix.lower()):
            relative=value[len(source_prefix):];assert relative in expected,(folder,relative)
            actual[relative]=sha(source/relative)
        else:
            assert value.lower().startswith(prefix.lower()),value
            relative=value[len(prefix):]
            assert relative in ['SR.Generated.cs','obj/Release/net8.0/Library.AssemblyInfo.cs',
                                'obj/Release/net8.0/.NETCoreApp,Version=v8.0.AssemblyAttributes.cs'],relative
            generated[relative]=sha(target/relative)
    assert actual==expected,(folder,set(expected)-set(actual),set(actual)-set(expected))
    assert len(generated)==3 and generated['SR.Generated.cs']==record['generated_sr_sha256'],folder
    references=[]
    for value in (target/'obj/Release/net8.0/reference-inputs.txt').read_text(encoding='utf-8-sig').splitlines():
        value=value.replace('\\','/')
        match=[(label,path,value[len(start):]) for label,path,start in roots if value.lower().startswith(start.lower())]
        assert len(match)==1,value
        label,path,relative=match[0]
        assert not relative.endswith('/System.Text.Json.dll'),value
        references.append(dict(origin=label,path=relative,sha256=sha(path/relative)))
    outputs={p.relative_to(target/'bin/Release/net8.0').as_posix():sha(p)
             for p in (target/'bin/Release/net8.0').rglob('*.dll')
             if p.name in [record['assembly']+'.dll',record['assembly']+'.resources.dll']}
    assert len(outputs)==(14 if folder!='Lib' else 1),(folder,outputs)
    record.update(actual_original_compile_items=actual,actual_generated_compile_items=generated,
                  actual_references=references,source_outputs=outputs,
                  implementation_sha256=sha(target/'bin/Release/net8.0'/(record['assembly']+'.dll')),
                  reference_sha256=sha(target/'obj/Release/net8.0/ref'/(record['assembly']+'.dll')))
    total+=len(actual)
assert total==497,total
for resource in json.loads((prepared/'localization.json').read_text()):
    name='Strings'+('.'+resource['culture'] if resource['culture'] else '')+'.resx'
    assert sha(prepared/resource['project']/name)==resource['prepared_sha256']
(prepared/'verified-build.json').write_text(json.dumps(dict(source_commit='81cabf2857a01351e5ab578947c7403a5b128ad1',
    source_archive_sha256='bbd5b1651bfc4c75b67ef23b71af58f6441401185f22233daefd35cc9ec72cfd',
    projects=records,actual_original_compile_items=total,production_cs_changes=[]),indent=2)+'\n')
print('PASS all497 actual original C# compiler items, four generated SR bindings/eight SDK metadata items and43 source DLL outputs')
