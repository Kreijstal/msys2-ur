"""Build the original VMR Standard2 reference-package closure; never runtime substitutes."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,xml.etree.ElementTree as E
source,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent;origin=json.loads((source/'source-inputs.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();native=lambda p:Path(p).resolve().as_posix()
for rel,r in origin['files'].items():assert sha(source/rel)==r['sha256'],rel
base=source/'src/source-build-reference-packages';packages=base/'src/referencePackages/src';projects={}
for p in packages.glob('*/*/*.csproj'):
    tree=E.parse(p);name=tree.findtext('.//AssemblyName');version=tree.findtext('.//PackageVersion');assert 'netstandard2.0' in tree.findtext('.//TargetFrameworks').split(';');projects[(name,version)]=(p,tree)
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll';platform=sorted((prefix/'lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll'));assert len(platform)==113
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent));records=[];outputs={};closures={};commands=[]
def build(key):
    if key in outputs:return
    original,tree=projects[key];name,version=key;deps=[]
    for group in tree.getroot().findall('ItemGroup'):
        if group.get('Condition') not in [None,"'$(TargetFramework)' == 'netstandard2.0'"]:continue
        for item in group.findall('ProjectReference'):
            dep=(original.parent/item.get('Include')).resolve();depkey=next(k for k,(p,_) in projects.items() if p==dep);build(depkey);deps.append(depkey)
    folder=out/name/version;folder.mkdir(parents=True);files=list((original.parent/'lib/netstandard2.0').glob('*.cs'))+list((original.parent/'ref/netstandard2.0').glob('*.cs'));assert len(files)==1
    assert 'ReferenceAssembly' in files[0].read_text(encoding='utf-8-sig'),key
    files.append(base/'src/SourceBuildAssemblyMetdata.cs')
    custom=original.parent/'Customizations.props'
    if custom.exists():
        for item in E.parse(custom).iter('Compile'):
            value=item.get('Include');assert value=='$(CommonSrc)IsExternalInit.cs';files.append(base/'src/referencePackages/common/IsExternalInit.cs')
    references={p.name:p for p in platform};selected={}
    def add(dep):
        n,v=dep
        if n not in selected or tuple(map(int,v.split('.')))>tuple(map(int,selected[n][1].split('.'))):selected[n]=dep
    for dep in deps:
        add(dep)
        for transitive in closures[dep]:add(transitive)
    for dep in selected.values():references[dep[0]+'.dll']=outputs[dep]
    references.pop(name+'.dll',None);closures[key]=list(selected.values());keyname=tree.findtext('.//StrongNameKeyId') or 'Microsoft';snk=folder/'public.snk';snk.write_bytes(bytes.fromhex((here/(keyname+'.pubkey.hex')).read_text()))
    output=folder/(name+'.dll');args=['/nostdlib+','/target:library','/refonly','/unsafe+','/nullable:disable','/langversion:preview','/deterministic+','/publicsign+','/keyfile:"'+native(snk)+'"','/out:"'+native(output)+'"']+['/reference:"'+native(p)+'"' for p in references.values()]+['"'+native(p)+'"' for p in files]
    rsp=folder/'compile.rsp';rsp.write_text('\n'.join(args)+'\n')
    cmd=[host,compiler,'-noconfig','@'+native(rsp)]
    with (folder/'compile.log').open('w',encoding='utf-8') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=120)
    commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==0,(key,r.returncode,folder/'compile.log')
    records.append(dict(assembly=name,package_version=version,original_framework='netstandard2.0',reference_only=True,original_source_sha256={p.relative_to(source).as_posix():sha(p) for p in files},original_project_sha256=sha(original),actual_reference_sha256={native(p):sha(p) for p in references.values()},output=native(output),output_sha256=sha(output),original_project_dependencies=[dict(id=n,version=v) for n,v in deps],original_production_source_changes=0));outputs[key]=output
    (out/'progress.json').write_text(json.dumps(records,indent=2)+'\n');print('PASS original reference-only',name,version,flush=True)
build(('System.Text.Json','8.0.5'))
(out/'results.json').write_text(json.dumps(dict(projects=records,commands=commands,vmr_commit=origin['vmr_commit'],original_target='netstandard2.0',runtime_implementation_substitution=False,original_runtime_framework_profiles_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS original JSON8 NS2 reference closure:',len(records),'assemblies')
