"""Audit all original task/profile/policy/resource inputs and source dependency/output bytes."""
from pathlib import Path
import hashlib,json,sys,tarfile
archive,plan,build,localized,out=(Path(p).resolve() for p in sys.argv[1:]);here=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();inputs=json.loads((plan/'source-inputs.json').read_text());source=Path(inputs['source_root']);records=json.loads((build/'results.json').read_text());translations=json.loads((localized/'results.json').read_text());models=json.loads((plan/'evaluated.json').read_text());wanted=dict(inputs['original_project_inputs_sha256']);count=0
assert sha(archive)==inputs['source_archive_sha256']=='9eb1139d9abecfab7d69fd7b02cb58d20792a0cd46ffb7b2ea6a12bbfda48f12'
for r in records['projects']:
 name=r['assembly'];wanted.update(r['original_source_sha256']);wanted.update(r['original_resource_sha256']);count+=len(r['original_source_sha256'])
 for rel,h in r['actual_reference_sha256'].items():assert sha(Path(rel))==h,rel
 for ext,h in r['output_assets_sha256'].items():assert sha(build/'bin'/(name+'.'+ext))==h,name
 props=models[name]['properties'];assert props['TargetFrameworks']==props['TargetFramework']=='net10.0';assert props['MicrosoftBuildVersion']=='18.3.0-release-26113-113'
 if props['ApplicationManifest']:
  original=source/'src/NuGet.Core'/name/props['ApplicationManifest'];wanted[original.relative_to(source).as_posix()]=sha(original);assert '/win32manifest:' in (build/name/'compile.rsp').read_text()
for rel,h in translations['original_xlf_sha256'].items():wanted[rel]=h
found={}
with tarfile.open(archive) as t:
 for m in t:
  rel=m.name.partition('/')[2]
  if m.isfile() and rel in wanted:found[rel]=hashlib.sha256(t.extractfile(m).read()).hexdigest()
assert set(found)==set(wanted)
for rel,h in wanted.items():assert sha(source/rel)==found[rel]==h,rel
for rel,h in translations['satellite_sha256'].items():assert sha(build/'bin'/rel)==h,rel
for asset in records['dependency_assets']:
 assert sha(Path(asset['output']))==asset['output_sha256']
 if 'archive' in asset:assert sha(Path(asset['archive']))==asset['archive_sha256']
policy=json.loads((here/'policy/sha256.json').read_text())
for rel,h in policy['files'].items():assert sha(here/'policy'/rel)==h,rel
assert count==77 and len(translations['satellite_sha256'])==39
out.write_text(json.dumps(dict(original_compile_items=count,unique_original_compile_inputs=len({p for r in records['projects'] for p in r['original_source_sha256']}),selected_archive_inputs_verified=len(wanted),original_xlf_inputs=len(translations['original_xlf_sha256']),source_profile_policy_resource_manifest_reference_output_and_satellite_hashes_verified=True,original_VMR_version_flow_policy=policy,original_production_source_changes=0,formal_package_built=False,full_nuget73_closure_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS77 original NuGet task/resolver compiler items,exact source/profile/resource/manifest/XLF inputs and source reference/output hashes')
