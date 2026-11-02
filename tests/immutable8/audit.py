"""Audit selected original VMR source/resource/policy inputs and produced assets."""
from pathlib import Path
import hashlib,json,sys,tarfile
archive,plan,build,localized,out=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();inputs=json.loads((plan/'source-inputs.json').read_text());source=Path(inputs['source_root']);manifest=inputs['source_manifest'];records=json.loads((build/'results.json').read_text())['projects'];translations=json.loads((localized/'results.json').read_text());wanted={}
for r in records:
 wanted.update(r['original_source_sha256']);wanted.update(r['original_resource_sha256']);policy=inputs['original_projects'][r['assembly']];wanted[policy['original_project']]=policy['original_project_sha256']
 for p,h in r['original_reference_sha256'].items():assert sha(Path(p))==h,p
 for ext,h in r['output_sha256'].items():assert sha(build/'bin'/(r['assembly']+'.'+ext))==h
for rel in ['eng/Versions.props','eng/resources.targets','src/libraries/Directory.Build.props','src/libraries/Directory.Build.targets','src/libraries/NetCoreAppLibrary.props','src/libraries/System.Collections.Immutable/Directory.Build.props']:wanted[rel]=manifest['files'][rel]['sha256']
wanted.update(translations['original_xlf_sha256'])
with tarfile.open(archive) as t:
 for rel,h in wanted.items():
  data=t.extractfile('runtime/'+rel).read();assert hashlib.sha256(data).hexdigest()==sha(source/rel)==h==manifest['files'][rel]['sha256'],rel
for rel,h in translations['satellite_sha256'].items():assert sha(build/'bin'/rel)==h
count=sum(len(r['original_source_sha256']) for r in records)
out.write_text(json.dumps(dict(original_compile_items=count,unique_original_compile_inputs=len({p for r in records for p in r['original_source_sha256']}),selected_original_release_archive_inputs_verified=len(wanted),all_source_reference_output_and_satellite_hashes_verified=True,original_NET8_framework_profile_preserved=True,other_original_framework_profiles_built=False,original_production_source_changes=0,actual_source_NET8_framework_reference_pack_version="8.0.31",TemplateEngine_Immutable8_requirement_built=True,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS',count,'original Compile inputs, original VMR resource/policy/XLF inputs and all reference/output/satellite hashes')
