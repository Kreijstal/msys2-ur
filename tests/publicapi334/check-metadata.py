"""Compare original published public CLR and nullable metadata with source-built NS2 analyzers."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,zipfile,xml.etree.ElementTree as E
build,published,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent;native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap';toolrefs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(toolrefs)==167;refs=sorted((prefix/'lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll'));assert len(refs)==113
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent));commands=[];records={}
def run(label,cmd):
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=150)
    commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode));return r.returncode
for n in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp']:shutil.copyfile(compiler/(n+'.dll'),out/(n+'.dll'))
args=['/nostdlib+','/target:exe','/nullable:enable','/out:"'+native(out/'Api.dll')+'"']+['/reference:"'+native(p)+'"' for p in toolrefs+[out/(n+'.dll') for n in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp']]]+['"'+native(here/'CompareApi.cs')+'"']
(out/'tool.rsp').write_text('\n'.join(args)+'\n');assert run('tool',[host,compiler/'csc.dll','-noconfig','@'+native(out/'tool.rsp')])==0
(out/'Api.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
with zipfile.ZipFile(published) as z:
    contracts={}
    for name in ['Microsoft.CodeAnalysis.PublicApiAnalyzers','Microsoft.CodeAnalysis.PublicApiAnalyzers.CodeFixes']:
        member=next(m for m in z.namelist() if m.endswith('/'+name+'.dll'))
        target=out/(name+'.published-metadata-only.dll');target.write_bytes(z.read(member));contracts[name]=target
reference_dir=out/'refs';reference_dir.mkdir()
for ref in refs+list((build/'dependencies').glob('*.dll'))+list((build/'bin').glob('*.dll')):
    shutil.copyfile(ref,reference_dir/ref.name)
for name,contract in contracts.items():
    result=out/(name+'.json')
    rc=run(name+'-metadata-compare',[host,out/'Api.dll',contract,build/'bin'/(name+'.dll'),reference_dir,result])
    record=json.loads(result.read_text());records[name]=dict(exit_code=rc,comparison=record,published_metadata_only_SHA256=sha(contract),produced_SHA256=sha(build/'bin'/(name+'.dll')))
    print(name,record['expected_entries'],record['total_differences'],len(record['nullable_annotation_differences']),flush=True)
(out/'results.json').write_text(json.dumps(dict(projects=records,commands=commands,published_assemblies_inspected_as_metadata_only=True,published_assemblies_not_executed_or_used_to_compile_production_libraries=True,full_dependency_goal_complete=False),indent=2)+'\n')
assert all(r['exit_code']==0 for r in records.values())
