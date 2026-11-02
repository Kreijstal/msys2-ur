"""Audit original NuGet6.13.2 source/profile/resources and compiler dependency/output bytes."""
from pathlib import Path
import hashlib,json,sys,tarfile
archive,plan,build,localized,out=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();inputs=json.loads((plan/'source-inputs.json').read_text());source=Path(inputs['source_root']);results=json.loads((build/'results.json').read_text());wanted=dict(inputs['original_project_inputs_sha256']);assets={}
for r in results['projects']:
 wanted.update(r['original_source_sha256']);wanted.update(r['original_resource_sha256'])
 for p,h in r['actual_reference_sha256'].items():assert sha(Path(p))==h,p
 for ext in ['dll','pdb','xml']:
  f=build/'bin'/(r['assembly']+'.'+ext);assert f.is_file();assets[f.name]=sha(f)
 assert assets[r['assembly']+'.dll']==r['output_sha256']
for rel in ['Directory.Packages.props','keys/35MSSharedLib1024.snk']:wanted[rel]=sha(source/rel)
with tarfile.open(archive) as t:
 for rel,h in wanted.items():assert hashlib.sha256(t.extractfile('NuGet.Client-5d81cb8da82eda8a6b47aae92d1e6f888de982ce/'+rel).read()).hexdigest()==sha(source/rel)==h,rel
assert not list(source.rglob('*.xlf'))
count=sum(len(r['original_source_sha256']) for r in results['projects'])
report=dict(original_compile_items=count,unique_original_compile_inputs=len({p for r in results['projects'] for p in r['original_source_sha256']}),selected_original_archive_inputs_verified=len(wanted),original_source_resource_project_policy_key_and_reference_hashes_verified=True,production_output_sha256=assets,original_production_source_changes=0,original_NET10_source_only_profile_retained=True,original_per_project_nullable_and_NoWarn_policy_retained=True,original_source_contains_no_XLF_files=True,published_external_localization_package_rebuilt=False,original_NS2_NET472_NET8_profiles_built=False,full_upstream_test_and_analyzer_integration=False,full_dependency_goal_complete=False)
out.write_text(json.dumps(report,indent=2)+'\n');print('PASS',count,'original compiler inputs,',len(wanted),'source/archive/policy/resource inputs and21 DLL/PDB/XML hashes')
