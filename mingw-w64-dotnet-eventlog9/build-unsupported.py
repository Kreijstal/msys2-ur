"""Run runtime9-pinned Arcade's original unsupported-assembly generator."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as E

root,tools=(Path(p).resolve() for p in sys.argv[1:])
out=root/'unsupported-build';out.mkdir()
source=root/'r';libs=source/'src/libraries';name='System.Diagnostics.EventLog'
here=Path(__file__).resolve().parent
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip())
native=lambda p:Path(p).resolve().as_posix()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
host=prefix/'lib/dotnet/dotnet.exe';host10=prefix/'lib/dotnet10/dotnet.exe'
refs=prefix/'lib/dotnet/reference-packs/runtime-9.0.11/ref/net9.0'
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),MSBuildEnableWorkloadResolver='false')
commands=[]
def run(label,command):
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:
        result=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
    commands.append(dict(label=label,command=[str(x) for x in command],exit_code=result.returncode))
    assert result.returncode==0,(label,result.returncode)

project=E.Element('Project');pg=E.SubElement(project,'PropertyGroup')
for k,v in dict(GeneratePlatformNotSupportedAssemblyMessage='SR.PlatformNotSupported_EventLog',GenFacadesRoslynAssembliesPath=native(prefix/'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap'),LangVersion='13.0').items():E.SubElement(pg,k).text=v
E.SubElement(project,'Import',Project=native(tools/'arcade/src/Microsoft.DotNet.GenFacades/build/Microsoft.DotNet.GenFacades.targets'))
# Keep original targets; bind the task to its private NET8 bootstrap output.
E.SubElement(E.SubElement(project,'PropertyGroup'),'GenFacadesTargetAssemblyPath').text=native(tools/'build/bin/Release/net8.0/Microsoft.DotNet.GenFacades.dll')
items=E.SubElement(project,'ItemGroup');contracts=[];generated=[]
for suffix in ['.cs','.netcoreapp.cs']:
    original=libs/name/'ref'/(name+suffix);contracts.append(original)
    destination=out/(name+suffix+'.notsupported.cs');generated.append(destination)
    E.SubElement(E.SubElement(items,'GenFacadeNotSupportedCompileInput',Include=native(original)),'OutputPath').text=native(destination)
E.SubElement(project,'Target',Name='_GetGenFacadeNotSupportedCompileInputs')
path=out/'Generate.proj';E.ElementTree(project).write(path,encoding='utf-8',xml_declaration=True)
run('generate',[host,'msbuild',native(path),'-t:AddGenFacadeNotSupportedCompileItem','-nologo','-v:minimal'])
model=json.loads((root/'plan-generic/evaluated.json').read_text())[name]
assert model['properties']['TargetFramework']=='net9.0'
assert not model['items']['ProjectReference'] and not model['items']['PackageReference']
originals=list(dict.fromkeys(Path(i['full_path']).resolve() for i in model['items']['Compile']))
assert originals and all(p.is_file() and p.is_relative_to(source) for p in originals)
originals.append(libs/'Common/src/System/SR.cs')
info=out/'AssemblyInfo.g.cs';info.write_text((root/'build/AssemblyInfo.g.cs').read_text()+'\n[assembly:System.Reflection.AssemblyMetadata("NotSupported","True")]\n')
files=originals+generated+[root/'build/SR.Generated.cs',info]
defines=model['properties']['DefineConstants'].split(';')+['NET','NETCOREAPP','NET9_0','NET8_0_OR_GREATER','NET9_0_OR_GREATER']
args=['/nostdlib+','/target:library','/langversion:13.0','/nullable:disable','/unsafe+','/optimize+','/debug:portable','/publicsign+','/keyfile:"'+native(root/'build/Microsoft.pubkey')+'"','/out:"'+native(out/(name+'.dll'))+'"','/define:'+';'.join(dict.fromkeys(x for x in defines if x)),'/resource:"'+native(root/'build/Strings.resources')+'",FxResources.'+name+'.SR.resources']
args+=['/reference:"'+native(p)+'"' for p in sorted(refs.glob('*.dll'))]+['"'+native(p)+'"' for p in files]
rsp=out/'compile.rsp';rsp.write_text('\n'.join(args)+'\n',encoding='utf-8')
env.update(DOTNET_ROOT=native(host10.parent),DOTNET_ROOT_X64=native(host10.parent),DOTNET_HOST_PATH=native(host10))
run('compile',[host10,prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll','-noconfig','@'+native(rsp)])
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_target='net9.0',original_contract_sha256={p.relative_to(source).as_posix():sha(p) for p in contracts},original_selected_cs_sha256={p.relative_to(source).as_posix():sha(p) for p in originals},generated_source_sha256={p.name:sha(p) for p in generated},task_sha256=sha(tools/'build/bin/Release/net8.0/Microsoft.DotNet.GenFacades.dll'),output_sha256=sha(out/(name+'.dll')),original_arcade_commit='6666973b629b24e259162dba03486c23af464bab',original_generator_framework='net9.0',bootstrap_generator_framework='net8.0',full_original_generator_profiles_built=False,full_dependency_goal_complete=False),indent=2)+'\n',encoding='utf-8')
print('PASS original NET9 unsupported-platform assembly generated with runtime9-pinned Arcade sources')
