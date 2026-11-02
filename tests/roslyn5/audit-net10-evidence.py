"""Verify original NET10 compiler source selections against the pinned archive."""
from pathlib import Path
import hashlib,json,sys,tarfile

evidence=Path(sys.argv[1]);source_archive=Path(sys.argv[2]);output=Path(sys.argv[3])
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(source_archive.read_bytes())=='e28cee5a55aaceccb555c8e1b583a8877d88002dde2468801b8d3f17463f2efb'
with tarfile.open(evidence) as t:
 read=lambda n:t.extractfile(n).read()
 load=lambda n:json.loads(read(n))
 manifest=load('roslyn53-net10-evidence-files.json')
 for n,d in manifest.items():assert sha(read(n))==d,n
 status=load('roslyn53-net10-build4/build-status.json')
 model=load('roslyn53-net10-plan1/evaluated.json')
 assert set(status)==set(model)=={'Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp','csc'}
 expected={};counts={}
 for name,r in status.items():
  selected={i['full_path'].replace('\\','/').split('/roslyn-source/',1)[1] for i in model[name]['items']['Compile']}
  assert selected==set(r['original_project_sources_sha256']),name
  assert model[name]['properties']['TargetFramework']=='net10.0'
  for n,d in r['original_project_sources_sha256'].items():
   assert n not in expected or expected[n]==d
   expected[n]=d
  counts[name]=len(selected)
  product='roslyn53-net10-build4/bin/'+name+'.dll'
  assert sha(read(product))==r['output_sha256'],name
  for n,d in r['generated_sources_sha256'].items():
   relative=n.replace('\\','/').split('/roslyn53-net10-build4/',1)[1]
   assert sha(read('roslyn53-net10-build4/'+relative))==d,n
 assert counts=={'Microsoft.CodeAnalysis':1042,'Microsoft.CodeAnalysis.CSharp':1151,'csc':11}
 for n,d in load('roslyn53-net10-plan1/original-inputs.json')['original_inputs_sha256'].items():expected[n]=d
 verified=set()
 with tarfile.open(source_archive) as source:
  for member in source:
   if not member.isfile():continue
   relative=member.name.split('/',1)[-1]
   if relative in expected:
    assert sha(source.extractfile(member).read())==expected[relative],relative
    verified.add(relative)
 assert verified==set(expected),sorted(set(expected)-verified)
 results=load('roslyn53-net10-cli-check1 λ/results.json')
 assert results['real_net10_cli_execution_passed'] and results['csharp14_and_source_regex_generation_passed']
 assert [c['exit_code'] for c in results['commands']]==[0,0,0,1]
 assert 'CS0103' in read('roslyn53-net10-cli-check1 λ/negative.log').decode()
 assert not results['original_cli_profile_complete'] and not results['full_sdk10_built']
 record=dict(evidence_members_verified=len(manifest),evidence_archive_sha256=sha(evidence.read_bytes()),original_archive_inputs_verified=len(verified),original_project_compile_items=counts,all_original_selected_sources_match_pinned_archive=True,all_recorded_products_and_emitted_regex_sources_match_evidence=True,real_net10_cli_execution_passed=True,commands=results['commands'],formal_net10_compiler_package_built=False,all_localized_satellites_and_cli_integration_audited=False,full_sdk10_built=False,full_dependency_goal_complete=False)
 output.write_text(json.dumps(record,indent=2)+'\n')
 print('PASS NET10 compiler evidence: '+str(len(manifest))+' members, '+str(len(verified))+' pinned source/project inputs, three compiler products and real CLI execution')
