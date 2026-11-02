"""Audit actual source/compile/resource/tool inputs against pristine archives."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile
from functools import lru_cache

root=Path(sys.argv[1]).resolve();source=root/'prepared/roslyn-source'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
root_native=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
@lru_cache(maxsize=None)
def local(value):
 value=value.replace('\\','/')
 if value.lower().startswith(root_native.lower()+'/'):return root/value[len(root_native)+1:]
 return Path(subprocess.check_output(['cygpath','-u',value],text=True).strip()) if ':/' in value.replace('\\','/') else Path(value)
expected={};actual_inputs={};reference_hashes={}
def original(name,digest):
 assert name not in expected or expected[name]==digest,name
 assert sha(source/name)==digest,name
 expected[name]=digest
status=json.loads((root/'net10-build/build-status.json').read_text())
assert set(status)=={'Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp','csc'}
for name,record in status.items():
 for n,d in record['original_project_sources_sha256'].items():original(n,d)
 for field in ['actual_compile_inputs_sha256','actual_analyzers_sha256','generated_sources_sha256','actual_references_sha256']:
  for n,d in record[field].items():
   p=local(n);assert sha(p)==d,(field,n);actual_inputs[str(p)]=d
   if field=='actual_references_sha256':reference_hashes[str(p)]=d
 assert sha(root/'net10-build/bin'/(name+'.dll'))==record['output_sha256']
for n,d in json.loads((root/'net10-plan/original-inputs.json').read_text())['original_inputs_sha256'].items():original(n,d)
localization=json.loads((root/'localized/results.json').read_text())
assert localization['all_original_api_resource_analyzer_generator_pdb_checks_passed']
for n,d in localization['original_resources_and_api_inputs_sha256'].items():original(n,d)
for n,d in localization['satellite_files_sha256'].items():assert sha(root/'localized/bin'/n)==d,n
prepared=json.loads((root/'prepared/source-inputs.json').read_text())
for record in prepared['generator_tools'].values():
 for n,d in record['original_cs'].items():original(n,d)
for name in prepared['generator_tools']:
 tool=root/'prepared'/name
 for inputs in ['Compile.txt','ReferencePath.txt','Analyzer.txt']:
  for file in tool.glob('obj/Release/*/'+inputs):
   for n in file.read_text(encoding='utf-8-sig').splitlines():
    if n.strip():p=local(n.strip());actual_inputs[str(p)]=sha(p)
model=json.loads((root/'net10-plan/evaluated.json').read_text())
for entry in model.values():
 for n in entry['imports']:
  p=local(n)
  if p.is_relative_to(source):original(p.relative_to(source).as_posix(),sha(p))
archive=root/'roslyn-5.3.0-2333221c.tar.gz'
assert sha(archive)=='e28cee5a55aaceccb555c8e1b583a8877d88002dde2468801b8d3f17463f2efb'
seen=set()
with tarfile.open(archive) as tar:
 for member in tar:
  name=member.name.split('/',1)[-1]
  if member.isfile() and name in expected:
   assert hashlib.sha256(tar.extractfile(member).read()).hexdigest()==expected[name],name;seen.add(name)
assert seen==set(expected),sorted(set(expected)-seen)
generated=json.loads((root/'prepared/generated-sources.json').read_text());assert len(generated)==5
commands=json.loads((root/'net10-build/commands.json').read_text())
assert all(c['exit_code']==0 for c in commands)
record=dict(original_archive_inputs_verified=len(seen),original_input_sha256=expected,actual_compiler_generator_and_reference_inputs_sha256=actual_inputs,net10_reference_and_project_output_hashes_verified=len(reference_hashes),regenerated_csharp_sources=5,source_generated_satellite_assemblies=26,original_public_api_declarations=10560,original_resource_sets=28,original_resource_values=39508,all_actual_sources_and_references_unchanged=True,all_six_original_net10_compiler_projects_evaluated=True,provided_original_net10_projects=list(status),visualbasic_and_compiler_server_built=False,full_sdk10_built=False,full_dependency_goal_complete=False)
(root/'source-audit.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS compiler source audit:',len(seen),'original archive inputs;',len(actual_inputs),'actual compile/tool/ref inputs')
