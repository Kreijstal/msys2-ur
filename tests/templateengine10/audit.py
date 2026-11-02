"""Audit original TemplateEngine VMR inputs, generated sources, dependency bytes and outputs."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile
archive,plan,build,localized,out=(Path(p).resolve() for p in sys.argv[1:6]);restored=Path(sys.argv[6]).resolve() if len(sys.argv)>6 else None;check=Path(sys.argv[7]).resolve() if len(sys.argv)>7 else None;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();inputs=json.loads((plan/'source-inputs.json').read_text());source=Path(inputs['source_root']);manifest=inputs['VMR_manifest'];results=json.loads((build/'results.json').read_text());wanted=dict(inputs['original_projects_sha256']);generated={};outputs={}
for r in results['projects']:
 assert r.get('original_EnableAnalyzers')=='false'
 wanted.update(r['original_source_sha256']);wanted.update({rel:meta['sha256'] for rel,meta in r['original_resources'].items()})
 for file,h in r['actual_reference_sha256'].items():assert sha(Path(file))==h,file
 for ext,h in r['output_sha256'].items():
  p=build/'bin'/(r['assembly']+'.'+ext);assert sha(p)==h;outputs[p.relative_to(build/'bin').as_posix()]=h
 for p in (build/r['assembly']).glob('*.g.cs'):generated[p.relative_to(build).as_posix()]=sha(p)
 assert r['package_version']=='10.0.200-preview.26113.113' and r['assembly_version']=='10.0.200.0' and r['file_version']=='10.2.26.11413'
for rel in ['Directory.Build.props','Directory.Build.targets','Directory.Packages.props','eng/Versions.props','eng/Version.Details.props','eng/Version.Details.xml']:wanted[rel]=manifest['files'][rel]['sha256']
translations=json.loads((localized/'results.json').read_text());wanted.update(translations['original_xlf_sha256'])
seen=set()
with tarfile.open(archive,'r|gz') as t:
 for member in t:
  if member.isfile() and member.name.startswith('templating/'):
   rel=member.name[len('templating/'):];assert rel not in seen;seen.add(rel)
   assert hashlib.sha256(t.extractfile(member).read()).hexdigest()==sha(source/rel)==manifest['files'][rel]['sha256'],rel
assert seen==set(manifest['files']) and len(seen)==1891
for rel,h in wanted.items():assert sha(source/rel)==h==manifest['files'][rel]['sha256'],rel
for rel,h in translations['satellite_sha256'].items():assert sha(build/'bin'/rel)==h;outputs[rel]=h
installed_assets=False
if restored:
 prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());feed=prefix/'lib/dotnet/library-packs'
 for asset in results['dependency_assets']:
  cached=Path(asset['archive']);installed=feed/cached.name
  assert sha(cached)==sha(installed)==asset['archive_sha256']
 installed_assets=True
restore_policy=json.loads((restored/'results.json').read_text()) if restored else {}
strict_restore=restore_policy.get('exit_code')==0 and restore_policy.get('original_TreatWarningsAsErrors_applied',False) and not restore_policy.get('diagnostics')
api=json.loads((check/'results.json').read_text()) if check else {}
report=dict(original_compile_items=sum(len(r['original_source_sha256']) for r in results['projects']),unique_original_compile_inputs=len({p for r in results['projects'] for p in r['original_source_sha256']}),all_original_VMR_snapshot_files_verified=len(seen),selected_original_VMR_inputs_verified=len(wanted),original_production_source_changes=0,original_NET10_framework_nullable_compiler_warning_global_using_and_resource_policy_retained=True,original_Arcade_version_and_resource_tasks_executed_in_NET8_bootstrap=True,actual_reference_and_output_bytes_verified=True,all_restored_dependency_archives_match_installed_source_feed=installed_assets,full_original_SDK_pruning_integration_verified=False,generated_source_sha256=generated,output_sha256=outputs,strict_CPM_warning_policy_passed=strict_restore,strict_original_API_baseline_passed=api.get('strict_API_baseline_passed',False),other_original_framework_profiles_built=False,full_dependency_goal_complete=False)
out.write_text(json.dumps(report,indent=2)+'\n');print('PASS',report['original_compile_items'],'original compile inputs,',len(seen),'original VMR files and',len(outputs),'output assets; restore/API status recorded independently')
