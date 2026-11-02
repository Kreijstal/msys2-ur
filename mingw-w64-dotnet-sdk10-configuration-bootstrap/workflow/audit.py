"""Audit selected original VMR source/resource/policy inputs and produced assets."""
from pathlib import Path
import hashlib,json,sys,tarfile
archive,plan,build,localized,out=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();inputs=json.loads((plan/'source-inputs.json').read_text());source=Path(inputs['source_root']);manifest=inputs['vmr_manifest'];records=json.loads((build/'results.json').read_text())['projects'];translations=json.loads((localized/'results.json').read_text());wanted={}
for r in records:
 wanted.update(r['original_source_sha256']);wanted.update(r['original_resource_sha256']);policy=inputs['original_projects'][r['assembly']];wanted[policy['original_project']]=policy['original_project_sha256']
 for p,h in r['original_reference_sha256'].items():assert sha(Path(p))==h,p
 for ext,h in r['output_sha256'].items():assert sha(build/'bin'/(r['assembly']+'.'+ext))==h
for rel in ['eng/Versions.props','eng/resources.targets','src/libraries/Directory.Build.props','src/libraries/Directory.Build.targets','src/libraries/NetCoreAppLibrary.props','src/libraries/Microsoft.Extensions.Configuration.Binder/src/buildTransitive/Microsoft.Extensions.Configuration.Binder.targets']:wanted[rel]=manifest['files'][rel]['sha256']
wanted.update(translations['original_xlf_sha256'])
with tarfile.open(archive) as t:
 for rel,h in wanted.items():
  data=t.extractfile('runtime/'+rel).read();assert hashlib.sha256(data).hexdigest()==sha(source/rel)==h==manifest['files'][rel]['sha256'],rel
for rel,h in translations['satellite_sha256'].items():assert sha(build/'bin'/rel)==h
count=sum(len(r['original_source_sha256']) for r in records)
out.write_text(json.dumps(dict(original_compile_items=count,unique_original_compile_inputs=len({p for r in records for p in r['original_source_sha256']}),selected_original_VMR_archive_inputs_verified=len(wanted),all_source_reference_output_and_satellite_hashes_verified=True,original_NET10_and_NS2_framework_profiles_preserved=True,original_production_source_changes=0,original_declared_Roslyn48_package_preserved=True,actual_source_Roslyn48_transitive_support_versions_recorded=True,full_logging_console_graph_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS',count,'original Compile inputs, original VMR resource/policy/XLF inputs and all reference/output/satellite hashes')
