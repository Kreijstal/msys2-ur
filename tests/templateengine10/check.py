"""Execute the original TemplateEngine closure with owned files and source-restored runtime assets."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,zipfile
plan,restored,build,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent;native=lambda p:Path(p).resolve().as_posix();source=Path(json.loads((plan/'source-inputs.json').read_text())['source_root']);prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap';binary=out/'bin';binary.mkdir();records=json.loads((build/'results.json').read_text())['projects'];baselines=out/'baselines';baselines.mkdir();api_inputs={};runtime_assets=[]
for r in records:
 name=r['assembly'];shutil.copyfile(build/'bin'/(name+'.dll'),binary/(name+'.dll'));text=[]
 for label in ['Shipped','Unshipped']:
  file=source/'src'/name/('PublicAPI.'+label+'.txt');assert file.is_file();text.append(file.read_text(encoding='utf-8-sig'));api_inputs[file.relative_to(source).as_posix()]=hashlib.sha256(file.read_bytes()).hexdigest()
 (baselines/(name+'.txt')).write_text('\n'.join(text)+'\n')
assets=json.loads((restored/'obj/project.assets.json').read_text())
for identity,meta in assets['libraries'].items():
 name,version=identity.split('/');archive=restored/'cache'/name.lower()/version/(name.lower()+'.'+version+'.nupkg');target=assets['targets']['net10.0'][identity];members=[m for m in target.get('runtime',{}) if m.endswith('.dll')]
 for m,info in target.get('runtimeTargets',{}).items():
  if m.endswith('.dll') and info.get('rid') in ['win','win-x64'] and info.get('assetType')=='runtime':members=[m]
 with zipfile.ZipFile(archive) as z:
  for member in members:
   data=z.read(member);(binary/Path(member).name).write_bytes(data);runtime_assets.append(dict(id=name,version=version,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),member=member,member_sha256=hashlib.sha256(data).hexdigest()))
for n in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp']:shutil.copyfile(compiler/(n+'.dll'),binary/(n+'.dll'))
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
selected={p.name:p for p in [*binary.glob('*.dll'),*refs]};args=['/nostdlib+','/target:exe','/nullable:enable','/langversion:preview','/out:"'+native(binary/'Check.dll')+'"']+['/reference:"'+native(p)+'"' for p in selected.values()]+['"'+native(here/n)+'"' for n in ['Check.cs','CheckApi.cs']];(out/'compile.rsp').write_text('\n'.join(args)+'\n');(binary/'Check.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))));commands=[]
api_exit=None
for label,cmd in [('compile',[host,compiler/'csc.dll','-noconfig','@'+native(out/'compile.rsp')]),('api',[host,binary/'Check.dll',refs[0].parent,baselines,out/'owned-work','api']),('execute',[host,binary/'Check.dll',refs[0].parent,baselines,out/'owned-work','runtime-only'])]:
 with (out/(label+'.log')).open('w',encoding='utf-8') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),NUGET_PACKAGES=native(out/'owned-packages'),NUGET_HTTP_CACHE_PATH=native(out/'owned-http-cache')),timeout=180)
 commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode))
 if label=='api':api_exit=r.returncode
 else:assert r.returncode==0,(label,r.returncode)
reports={p.name.removesuffix('.txt.report.json'):json.loads(p.read_text()) for p in baselines.glob('Microsoft.*.txt.report.json')}
restore_policy=json.loads((restored/'results.json').read_text())
strict_restore=restore_policy['exit_code']==0 and restore_policy['original_TreatWarningsAsErrors_applied'] and not restore_policy.get('diagnostics')
(out/'results.json').write_text(json.dumps(dict(commands=commands,upstream_API_baseline_sha256=api_inputs,runtime_assets=runtime_assets,original_identities_verified=True,strict_API_baseline_exit_code=api_exit,strict_API_baseline_passed=api_exit==0,API_reports=reports,raw_extra_API_and_full_metadata_comparison_performed=False,owned_TemplateEngine_scan_generation_dryrun_search_json_and_cancellation_passed=True,strict_CPM_restore_policy_passed=strict_restore,full_original_SDK_pruning_integration_verified=False,full_upstream_test_suite_run=False,formal_packages_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print((out/'execute.log').read_text(encoding='utf-8'))

raise SystemExit(0 if api_exit==0 else 1)
