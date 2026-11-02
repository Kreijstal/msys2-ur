"""Validate the seven original NuGet6.13.2 NET10 libraries and owned protocol operations."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,zipfile
plan,dependency_restore,build,out=(Path(p).resolve() for p in sys.argv[1:5]);localization=None;out.mkdir();here=Path(__file__).resolve().parent
source=Path(json.loads((plan/'source-inputs.json').read_text())['source_root']);prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';native=lambda p:Path(p).resolve().as_posix()
binary=out/'bin';shutil.copytree(build/'bin',binary);baselines=out/'baselines';baselines.mkdir();originals={}
names=[p['assembly'] for p in json.loads((build/'results.json').read_text())['projects']]
for name in names:
    parts=[];folder=source/'src/NuGet.Core'/name
    # The archive's latest per-TFM API baseline is NET8; check it against NET10.
    if not (folder/'PublicAPI.Shipped.txt').exists():folder=folder/'PublicAPI/net8.0'
    for label in ['Shipped','Unshipped']:
        p=folder/('PublicAPI.'+label+'.txt')
        if p.exists():parts.append(p.read_text(encoding='utf-8-sig'));originals[p.relative_to(source).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    assert parts,name
    (baselines/(name+'.txt')).write_text('\n'.join(parts)+'\n')
# Runtime implementations replace the package's reference-only assets in the consumer.
runtime_assets=[]
restored=json.loads((dependency_restore/'results.json').read_text())
assets=json.loads((dependency_restore/'obj/project.assets.json').read_text())
for package,record in restored['actual_source_packages'].items():
 archive=Path(record['archive']);version=record['version'];assert hashlib.sha256(archive.read_bytes()).hexdigest()==record['archive_sha256']
 target=assets['targets']['net10.0'][package+'/'+version]
 members=[m for m in target.get('runtime',{}) if m.endswith('.dll')]
 for m,meta in target.get('runtimeTargets',{}).items():
  if m.endswith('.dll') and meta.get('rid') in ['win','win-x64'] and meta.get('assetType')=='runtime':members=[m]
 with zipfile.ZipFile(archive) as z:
  for member in members:
   data=z.read(member);(binary/Path(member).name).write_bytes(data);runtime_assets.append(dict(archive=native(archive),archive_sha256=record['archive_sha256'],member=member,member_sha256=hashlib.sha256(data).hexdigest()))
compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap'
for name in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp']:shutil.copyfile(compiler/(name+'.dll'),binary/(name+'.dll'))
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
args=['/nostdlib+','/target:exe','/nullable:enable','/out:"'+native(binary/'Check.dll')+'"']+['/reference:"'+native(p)+'"' for p in list({p.name:p for p in [*binary.glob('*.dll'),*refs]}.values())]+['"'+native(here/n)+'"' for n in ['Check.cs','CheckApi.cs']]
rsp=out/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');(binary/'Check.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),NUGET_SCRATCH=native(out/'scratch'),NUGET_PACKAGES=native(out/'owned-work/packages'),NUGET_HTTP_CACHE_PATH=native(out/'http-cache'),NUGET_PLUGINS_CACHE_PATH=native(out/'plugins-cache'));commands=[]
for label,command in [('compile',[host,compiler/'csc.dll','-noconfig','@'+native(rsp)]),('execute',[host,binary/'Check.dll',source,refs[0].parent,baselines,out/'owned-work']+([localization] if localization else []))]:
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=240)
    commands.append(dict(label=label,command=[str(p) for p in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_public_api_baseline_sha256=originals,runtime_dependency_assets=runtime_assets,localized_values_checked=localization is not None,original_api_declarations_preserved=True,raw_extra_api_comparison_performed=False,owned_package_protocol_download_and_dependency_resolution_passed=True,exact_Immutable8_ProtectedData44_Pkcs604_compiled_assembly_bindings_verified=True,exact_source_dependencies_executed_in_isolated_context=True,full_upstream_test_suite_run=False,formal_NuGet6132_packages_built=False,full_sdk10_built=False,exact_Asn1801_source_runtime_and_strict_restore_verified=True,full_dependency_goal_complete=False),indent=2)+'\n')
print((out/'execute.log').read_text(encoding='utf-8'))
