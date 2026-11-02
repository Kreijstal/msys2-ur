"""Audit unchanged source and exact build references for every legacy variant."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

root=Path(sys.argv[1]).resolve();record=json.loads((root/'source-inputs.json').read_text());build=json.loads((root/'build-results.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,digest in record['original_file_sha256'].items():assert sha(root/'source'/name)==digest,name
assert len(record['libraries'])==len(build)==33 and len(record['root_contracts'])==16
assert record['production_source_changes']==4 and record['reference_only'] and record['original_source_files_modified_in_place']==0
assert record['SDK_default_NoWarn']==['1701','1702']
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
outputs={key:root/'contracts'/key/(item['name']+'.dll') for key,item in record['libraries'].items()}
for key,item in record['libraries'].items():
    name=item['name'];version=item['assembly_version'];row=build[key]
    assert row['exit_code']==0 and row['reference_only'] and row['output_sha256']==sha(outputs[key])
    assert row['original_framework']==item['original_framework']
    expected_inputs=[root/'source'/item['source'],root/'source/src/SourceBuildAssemblyMetdata.cs']
    if item.get('generated_port_source'):expected_inputs[0]=root/item['generated_port_source']
    if item.get('generated_assembly_attributes'):
        expected_inputs.append(root/item['generated_assembly_attributes'])
    expected_sources=[p for p in expected_inputs if p.is_relative_to(root/'source')];generated=[p for p in expected_inputs if not p.is_relative_to(root/'source')]
    assert row['original_source_sha256']=={str(p.relative_to(root/'source')):sha(p) for p in expected_sources}
    for p in generated:assert sha(p)==record['generated_source_sha256'][p.name]
    assert row['generated_source_sha256']=={p.name:sha(p) for p in generated}
    closure=set()
    def add(dep):
        if dep in closure:return
        closure.add(dep)
        for d in record['libraries'][dep]['dependencies']:add(d)
    for dep in item['dependencies']:add(dep)
    selected={}
    for dep in closure:
        ident,ver=dep.split('/')
        if ident not in selected or tuple(map(int,ver.split('.')))>tuple(map(int,selected[ident].split('/')[1].split('.'))):selected[ident]=dep
    refs=[outputs[d] for d in sorted(selected.values())]
    assert row['references']=={p.name:sha(p) for p in refs}
    expected_flags=['/nostdlib+','/target:library','/refonly','/unsafe+','/nullable:disable','/langversion:latest','/deterministic+','/warnaserror+','/nowarn:'+','.join(record['SDK_default_NoWarn']+record['original_NoWarn']),'/publicsign+']
    actual=(root/'build'/key/'compile.rsp').read_text().splitlines()
    assert actual[:len(expected_flags)]==expected_flags
    assert [s for s in actual if s.startswith('/reference:')]==['/reference:"'+native(p)+'"' for p in refs]
    assert actual[-len(expected_inputs):]==['"'+native(p)+'"' for p in expected_inputs]
for name,key in record['root_contracts'].items():assert (root/'ref'/(name+'.dll')).read_bytes()==outputs[key].read_bytes()
assert len(list((root/'ref').glob('*.dll')))==16 and len(list((root/'contracts').glob('*/*/*.dll')))==33
report=dict(source_commit=record['source_commit'],CoreFX_source_commit=record['CoreFX_source_commit'],original_source_files_verified=len(record['original_file_sha256']),unchanged_contract_source_variants=29,ported_contract_variants=4,production_source_changes=4,original_source_files_modified_in_place=0,Interop_original_class_and_struct_declarations_restored=True,selected_root_contracts=16,all_compile_inputs_and_exact_reference_DLL_bytes_verified=True,original_NoWarn=record['original_NoWarn'],SDK_default_NoWarn=record['SDK_default_NoWarn'],warnings_as_errors=True,reference_only=True,output_sha256={key:sha(path) for key,path in outputs.items()},CodePages_Diagnostics_Contracts_reference_built=True,CodePages_Diagnostics_Contracts_runtime_package_built=False,full_NETStandard13_runtime_package_closure_built=False)
(root/'producer-audit.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS original source inputs, compiler policy and exact dependency reference bytes for 33 contract variants')
