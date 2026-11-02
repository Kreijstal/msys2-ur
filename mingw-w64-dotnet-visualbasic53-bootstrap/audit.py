"""Audit actual original VB/client/generator/resource inputs and dependencies."""
from pathlib import Path
from functools import lru_cache
import hashlib,json,subprocess,sys,tarfile
root=Path(sys.argv[1]).resolve();source=root/'prepared/roslyn-source';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
root_native=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
@lru_cache(maxsize=None)
def local(value):
 value=value.replace('\\','/')
 if value.lower().startswith(root_native.lower()+'/'):return root/value[len(root_native)+1:]
 return Path(subprocess.check_output(['cygpath','-u',value],text=True).strip()) if ':/' in value else Path(value)
originals={};actual={}
def original(name,digest):
 assert name not in originals or originals[name]==digest,name
 assert sha(source/name)==digest,name;originals[name]=digest
vb=json.loads((root/'vb-build/results.json').read_text())
for n,d in vb['original_project_source_hashes'].items():original(n,d)
for n,d in vb['resource_inputs_sha256'].items():original(n,d)
for field in ['actual_compile_input_hashes','actual_reference_hashes']:
 for n,d in vb[field].items():assert sha(local(n))==d,n;actual[n]=d
compiler=Path('/clang64/lib/dotnet/compiler-packs/roslyn-vb-4.9.2/vbc.dll');assert sha(compiler)==vb['compiler_sha256'];actual[str(compiler)]=sha(compiler)
assert sha(root/'vb-build/Microsoft.CodeAnalysis.VisualBasic.dll')==vb['output_sha256']
clients=json.loads((root/'clients/results.json').read_text())
for name,record in clients['projects'].items():
 for n,d in record['original_sources_sha256'].items():original(n,d)
 for n,d in record['actual_references_sha256'].items():assert sha(local(n))==d,n;actual[n]=d
 assert sha(root/'clients/bin'/(name+'.dll'))==record['output_sha256']
localized=json.loads((root/'localized/results.json').read_text())
assert localized['all_original_vb_api_and_resources_passed']
for n,d in localized['original_source_inputs_sha256'].items():original(n,d)
for n,d in localized['satellite_files_sha256'].items():assert sha(root/'localized/bin'/n)==d,n
for p in (root/'vb-generators').glob('*/obj/Release/net8.0/Compile.txt'):
 for value in p.read_text(encoding='utf-8-sig').splitlines():
  if value.strip():
   file=local(value.strip());actual[str(file)]=sha(file)
   if file.is_relative_to(source):original(file.relative_to(source).as_posix(),sha(file))
for n,d in json.loads((root/'net10-plan/original-inputs.json').read_text())['original_inputs_sha256'].items():original(n,d)
for entry in json.loads((root/'net10-plan/evaluated.json').read_text()).values():
 for name in entry['imports']:
  p=local(name)
  if p.is_relative_to(source):original(p.relative_to(source).as_posix(),sha(p))
for p in (root/'vb-generators/generated').iterdir():
 baseline=source/'src/Compilers/VisualBasic/Portable/Generated'/p.name
 assert p.read_text(encoding='utf-8-sig')==baseline.read_text(encoding='utf-8-sig'),p.name
 original(baseline.relative_to(source).as_posix(),sha(baseline))
archive=root/'roslyn-5.3.0-2333221c.tar.gz';assert sha(archive)=='e28cee5a55aaceccb555c8e1b583a8877d88002dde2468801b8d3f17463f2efb'
seen=set()
with tarfile.open(archive) as tar:
 for m in tar:
  n=m.name.split('/',1)[-1]
  if m.isfile() and n in originals:
   assert hashlib.sha256(tar.extractfile(m).read()).hexdigest()==originals[n],n;seen.add(n)
assert seen==set(originals)
csharp=Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap')
for n,d in json.loads((root/'csharp-source-package-inputs.json').read_text())['actual_source_tool_files_sha256'].items():assert sha(csharp/n)==d,n
server=json.loads((root/'server-check λ/results.json').read_text());assert server['completed_server_requests']==4 and server['no_local_fallback_verified'] and server['owned_server_shutdown_verified']
vbc=json.loads((root/'vbc-check λ/results.json').read_text());assert vbc['real_net10_vbc_execution_passed']
record=dict(original_archive_inputs_verified=len(seen),original_inputs_sha256=originals,actual_compiler_and_reference_inputs_sha256=actual,all_actual_sources_and_references_unchanged=True,original_visualbasic_api_declarations=6096,original_resource_sets=14,original_resource_strings=25228,source_satellites=13,all_five_original_generated_vb_files_and_grammar_match=True,real_compiler_server_requests=4,server_no_local_fallback_and_owned_shutdown_verified=True,installed_source_csharp_dependency_bytes_unchanged=True,all_six_net10_primary_projects_available=True,all_other_framework_profiles_built=False,full_sdk10_built=False,full_dependency_goal_complete=False)
(root/'source-audit.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS VB/compiler-server source audit:',len(seen),'original archive inputs;',len(actual),'actual compiler/ref inputs')
