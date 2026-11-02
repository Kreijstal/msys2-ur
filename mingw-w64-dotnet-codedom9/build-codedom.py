"""Compile original CodeDom9 selected inputs against source NET9 contracts."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as E
plan,refs,out=(Path(p).resolve() for p in sys.argv[1:4]);assert not out.exists();out.mkdir()
here=Path(__file__).resolve().parent;prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());data=json.loads((plan/'source-inputs.json').read_text());source=Path(data['source_root']);libs=source/'src/libraries'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();native=lambda p:Path(p).resolve().as_posix()
model=json.loads((plan/'evaluated.json').read_text())['System.CodeDom'];assert model['properties']['TargetFramework']=='net9.0'
files=list(dict.fromkeys(Path(i['full_path']).resolve() for i in model['items']['Compile']));assert files and all(p.is_file() and p.is_relative_to(source) for p in files)
files.append(libs/'Common/src/System/SR.cs');originals={p.relative_to(source).as_posix():sha(p) for p in files}
ref_files=sorted(refs.glob('*.dll'));assert len(ref_files)==164
key=bytes.fromhex((here/'Open.pubkey.hex').read_text());assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='cc7b13ffcd2ddd51';(out/'Open.pubkey').write_bytes(key)
resources=libs/'System.CodeDom/src/Resources/Strings.resx';entries=list(E.parse(resources).iter('data'));logical='FxResources.System.CodeDom.SR'
code=['#nullable enable','namespace FxResources.System.CodeDom { internal static class SR {} }','namespace System { internal static partial class SR {','private static readonly global::System.Resources.ResourceManager s_resourceManager = new global::System.Resources.ResourceManager("'+logical+'", typeof(FxResources.System.CodeDom.SR).Assembly);','private static global::System.Resources.ResourceManager ResourceManager => s_resourceManager;']
for e in entries:
 n=e.get('name');assert n.isidentifier();code.append('internal static string @'+n+' => GetResourceString('+json.dumps(n)+');')
(out/'neutral-strings.json').write_text(json.dumps({e.get('name'):e.findtext('value') or '' for e in entries},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
code.append('}}');sr=out/'SR.Generated.cs';sr.write_text('\n'.join(code)+'\n',encoding='utf-8');files.append(sr)
info=out/'AssemblyInfo.g.cs';version=(source.parent/'file-version.txt').read_text().strip();attrs=['[assembly:System.CLSCompliant(true)]','[assembly:System.Reflection.AssemblyVersion("9.0.0.0")]','[assembly:System.Reflection.AssemblyFileVersion("'+version+'")]','[assembly:System.Reflection.AssemblyInformationalVersion("9.0.11+fa7cdded37981a97cec9a3e233c4a6af58a91c57")]','[assembly:System.Runtime.Versioning.TargetFramework(".NETCoreApp,Version=v9.0")]']
policy=E.parse(libs/'System.CodeDom/Directory.Build.props');platforms=policy.findtext('.//UnsupportedOSPlatforms').split(';')
for platform in platforms:attrs.append('[assembly:System.Runtime.Versioning.UnsupportedOSPlatform('+json.dumps(platform)+')]')
info.write_text('\n'.join(attrs)+'\n');files.append(info)
host8=prefix/'lib/dotnet/dotnet.exe';host10=prefix/'lib/dotnet10/dotnet.exe';sdk=host8.parent/'sdk/8.0.131';compiler=host8.parent/'compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
env=dict(os.environ,DOTNET_ROOT=native(host8.parent),DOTNET_ROOT_X64=native(host8.parent),DOTNET_HOST_PATH=native(host8),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1');commands=[]
def run(label,command):
 with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(label=label,command=[str(x) for x in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
project=E.Element('Project');E.SubElement(project,'UsingTask',TaskName='GenerateResource',AssemblyFile=native(sdk/'Microsoft.Build.Tasks.Core.dll'));target=E.SubElement(project,'Target',Name='Resources');E.SubElement(target,'GenerateResource',Sources=native(resources),OutputResources=native(out/'Strings.resources'),ExecuteAsTool='false');E.ElementTree(project).write(out/'Resources.proj',encoding='utf-8',xml_declaration=True)
run('resources',[host8,'msbuild',native(out/'Resources.proj'),'-t:Resources','-nologo','-v:minimal'])
defines=list(dict.fromkeys([x for x in model['properties']['DefineConstants'].split(';') if x]+['NET','NET9_0','NETCOREAPP',*['NET'+str(i)+'_0_OR_GREATER' for i in range(5,10)]]))
args=['/nostdlib+','/target:library','/langversion:preview','/nullable:disable','/unsafe+','/optimize+','/deterministic+','/debug:portable','/publicsign+','/keyfile:"'+native(out/'Open.pubkey')+'"','/out:"'+native(out/'System.CodeDom.dll')+'"','/define:'+';'.join(defines),'/resource:"'+native(out/'Strings.resources')+'",'+logical+'.resources']
args+=['/reference:"'+native(p)+'"' for p in ref_files]+['"'+native(p)+'"' for p in files];rsp=out/'compile.rsp';rsp.write_text('\n'.join(args)+'\n',encoding='utf-8')
env.update(DOTNET_ROOT=native(host10.parent),DOTNET_ROOT_X64=native(host10.parent),DOTNET_HOST_PATH=native(host10));run('compile',[host10,compiler,'-noconfig','@'+native(rsp)])
record=dict(commands=commands,original_selected_cs_sha256=originals,original_resource_sha256=sha(resources),original_project_sha256=data['original_project_sha256'],reference_sha256={p.name:sha(p) for p in ref_files},actual_compile_sha256={native(p):sha(p) for p in files},compiler_sha256=sha(compiler),output_sha256=sha(out/'System.CodeDom.dll'),original_target='net9.0',source_version='9.0.11',public_key_token='cc7b13ffcd2ddd51',neutral_resource_strings=len(entries),original_arcade_file_version=version,original_unsupported_platforms=platforms,original_production_cs_changes=0,original_cls_compliant=True,original_resource_scope_complete=True,localized_resource_sources_present=False,localized_satellites_built=False,formal_package_built=False,executed=False,full_msbuild_built=False,full_sdk10_built=False,full_dependency_goal_complete=False)
(out/'results.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print('PASS CodeDom9 original NET9 compilation:',len(originals),'source inputs;',len(entries),'neutral strings')
