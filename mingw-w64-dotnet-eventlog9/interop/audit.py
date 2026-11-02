"""Capture actual compiler inputs and verify original generator sources."""
from pathlib import Path
import hashlib,json,sys

root=Path(sys.argv[1]).resolve()
model=json.loads((root/'source-inputs.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=root/'r'
projects={}
for assembly,original in model['projects'].items():
    project=root/assembly
    inputs={}
    for kind in ['Compile','ReferencePath','Analyzer']:
        captured=project/'obj/Release/net8.0'/(kind+'.txt')
        paths=list(dict.fromkeys(Path(line).resolve() for line in captured.read_text(encoding='utf-8-sig').splitlines() if line.strip()))
        inputs[kind]={p.as_posix():sha(p) for p in paths}
    assert inputs['Compile'] and inputs['ReferencePath']
    originals={}
    generated={}
    for name,digest in inputs['Compile'].items():
        p=Path(name)
        if p.is_relative_to(source):
            relative=p.relative_to(source).as_posix()
            assert model['extracted_source_sha256'][relative]==digest,relative
            originals[relative]=digest
        else:
            assert p.is_relative_to(project),p
            generated[name]=digest
    assert set(original['default_cs_sha256'])<=set(originals)
    output=project/'bin/Release/net8.0'/(assembly+'.dll')
    projects[assembly]=dict(actual_inputs=inputs,original_cs_sha256=originals,bootstrap_generated_cs_sha256=generated,output_sha256=sha(output),original_target='netstandard2.0',bootstrap_target='net8.0',bootstrap_source_roslyn_package='4.9.2')
record=dict(source_commit=model['source_commit'],source_archive_sha256=model['source_archive_sha256'],projects=projects,production_source_changes=0,full_original_generator_profiles_built=False,full_dependency_goal_complete=False)
(root/'audit-results.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print('PASS actual original/generated source and reference inputs for both private NET8 interop generators')
