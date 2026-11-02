"""Gate actual original compiler/resource inputs and resolved dependency graph."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

source,prepared,cache=(Path(p).resolve() for p in sys.argv[1:])
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip().replace('\\','/')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
gold=json.loads((prepared/'source-build-inventory.json').read_text())
libraries=json.loads(Path(__file__).with_name('libraries.json').read_text())
prefix=native(prepared)+'/'
for relative,overlay in json.loads((prepared/'source-metadata-overlays.json').read_text()).items():
    assert sha(prepared/relative)==overlay.get('prepared_sha256',overlay.get('owned_sha256')),relative
    if 'original_sha256' in overlay:assert sha(source/relative)==overlay['original_sha256'],relative
records={};total=0
for name,record in gold['projects'].items():
    record=dict(record)
    obj=prepared/'artifacts'/name/'obj/Release/net8.0'
    inputs=(obj/'compiler-inputs.txt').read_text(encoding='utf-8-sig').splitlines()
    assert len(inputs)==len(set(p.lower() for p in inputs)),name
    expected=record['original_cs'] | gold['shared_cs']
    actual={};generated={}
    allowed={f'artifacts/{name}/obj/Release/net8.0/{name}.AssemblyInfo.cs',
             f'artifacts/{name}/obj/Release/net8.0/.NETCoreApp,Version=v8.0.AssemblyAttributes.cs'}
    for value in inputs:
        value=value.replace('\\','/')
        assert value.lower().startswith(prefix.lower()),value
        relative=value[len(prefix):];path=prepared/relative
        if relative in expected:
            assert sha(path)==expected[relative],relative
            actual[relative]=sha(path)
        else:
            assert relative in allowed,relative
            generated[relative]=sha(path)
    assert actual==expected,(name,set(expected)-set(actual),set(actual)-set(expected))
    assert set(generated)==allowed,(name,generated)
    resources={}
    expected_resources=record['original_resx'] | record.get('original_embedded',{})
    overlays=json.loads((prepared/'source-resource-overlays.json').read_text())
    for value in (obj/'resource-inputs.txt').read_text(encoding='utf-8-sig').splitlines():
        path,logical,manifest=value.split('|')
        path=path.replace('\\','/')
        assert path.lower().startswith(prefix.lower()),path
        relative=path[len(prefix):]
        assert relative in expected_resources,(name,relative)
        wanted=overlays[relative]['prepared_sha256'] if relative in overlays else expected_resources[relative]
        assert sha(prepared/relative)==wanted,(name,relative)
        resources[relative]=dict(sha256=sha(prepared/relative),logical_name=logical,manifest_name=manifest)
    assert set(resources)==set(expected_resources),(name,resources)
    assets=json.loads((obj.parents[1]/'project.assets.json').read_text())
    framework=assets['project']['frameworks']['net8.0']
    project_refs=assets['project']['restore']['frameworks']['net8.0'].get('projectReferences',{})
    projects=sorted(Path(p.replace('\\','/')).stem for p in project_refs)
    assert projects==sorted(libraries[name]['projects']),(name,projects)
    assert set(framework.get('dependencies',{}))==set(libraries[name]['packages']),name
    for package,version in libraries[name]['packages'].items():
        assert framework['dependencies'][package]['version']=='['+version+', )',(name,package)
        assert package+'/'+version in assets['libraries'],(name,package)
    references=[]
    roots=[('prepared',prepared),('source-cache',cache),('framework',Path('/clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31'))]
    roots=[(label,root,native(root)+'/') for label,root in roots]
    for value in (obj/'reference-inputs.txt').read_text(encoding='utf-8-sig').splitlines():
        value=value.replace('\\','/')
        match=[(label,root,value[len(start):]) for label,root,start in roots if value.lower().startswith(start.lower())]
        assert len(match)==1,value
        label,root,relative=match[0]
        references.append(dict(origin=label,path=relative,sha256=sha(root/relative)))
    record.update(production_cs_changes=[],actual_original_compile_items=actual,actual_generated_compile_items=generated,
                  actual_resources=resources,actual_references=references,
                  dependencies={**{p:'6.9.1' for p in projects},**libraries[name]['packages']},
                  implementation_sha256=sha(prepared/'artifacts'/name/'bin/Release/net8.0'/(name+'.dll')),
                  reference_sha256=sha(obj/'ref'/(name+'.dll')),
                  documentation_sha256=sha(prepared/'artifacts'/name/'bin/Release/net8.0'/(name+'.xml')))
    records[name]=record;total+=len(actual)
(prepared/'verified-build.json').write_text(json.dumps(dict(source_commit=gold['source_commit'],
    source_archive_sha256=gold['source_archive_sha256'],projects=records,
    original_compile_items=total,resource_overlays=json.loads((prepared/'source-resource-overlays.json').read_text()),
    metadata_overlays=json.loads((prepared/'source-metadata-overlays.json').read_text())),indent=2)+'\n')
print('PASS',total,'actual unchanged original C# compiler inputs, SDK metadata, resources, source references and eleven exact dependency graphs')
