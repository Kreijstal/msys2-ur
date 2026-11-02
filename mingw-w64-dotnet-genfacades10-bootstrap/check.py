"""Run original MSBuild task targets and execute their generated products."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,xml.etree.ElementTree as E
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir();here=Path(__file__).resolve().parent
product=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else root/'product'
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
dotnet='/clang64/lib/dotnet/dotnet.exe';compiler=Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap/CompilerHost.dll')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
commands=[]
def run(cmd,log,success=True):
 with log.open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env)
 commands.append(dict(command=cmd,exit_code=r.returncode,expected_success=success))
 assert (r.returncode==0)==success,(cmd,r.returncode,log)
 return r
refs=Path('/clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0')
assert refs.is_dir(),refs
core=Path('/clang64/lib/dotnet-bootstrap10/corelib/10.0.5/System.Private.CoreLib.dll')
net10refs=Path('/clang64/lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0')
def compile(name,files,references,exe=False):
 rsp=out/(name+'.rsp');dll=out/(name+'.dll')
 args=['/nostdlib+','/target:'+('exe' if exe else 'library'),'/deterministic+','/langversion:preview','/out:"'+native(dll)+'"']+['/reference:"'+native(p)+'"' for p in references]+['"'+native(p)+'"' for p in files]
 rsp.write_text('\n'.join(args)+'\n');run([dotnet,native(compiler),'-noconfig','@'+native(rsp)],out/(name+'-compile.log'));return dll
def msbuild(name,tree,success=True,target='GeneratePartialFacadeSource'):
 path=out/(name+'.proj');E.indent(tree);E.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)
 return run([dotnet,'msbuild',native(path),'-nologo','-t:'+target,'-v:minimal'],out/(name+'.log'),success)
def project():
 p=E.Element('Project');pg=E.SubElement(p,'PropertyGroup')
 E.SubElement(pg,'GenFacadesTargetAssemblyPath').text=native(product/'tools/net/Microsoft.DotNet.GenFacades.dll')
 E.SubElement(pg,'GenFacadesRoslynAssembliesPath').text=native(product/'tools/net')
 # Import the unchanged target providing the task's actual production invocation.
 E.SubElement(pg,'GeneratePartialFacadeSourceDependsOn').text=''
 E.SubElement(p,'Target',Name='GetGenFacadesRoslynAssembliesPath')
 E.SubElement(p,'Target',Name='ResolveMatchingContract')
 E.SubElement(p,'Import',Project=native(product/'build/Microsoft.DotNet.GenFacades.PartialFacadeSource.targets'))
 return p,pg
inspect=compile('Inspect',[here/'inputs/Inspect.cs'],sorted(refs.glob('*.dll')),True)
(out/'Inspect.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net8.0',framework=dict(name='Microsoft.NETCore.App',version='8.0.31')))))
def metadata(path,name):
 target=out/(name+'-metadata.json');run([dotnet,native(inspect),native(path)],target);return json.loads(target.read_text())
facades={}
for name in ['System.Buffers','System.Diagnostics.Debug','System.Runtime.CompilerServices.Unsafe','System.Runtime.InteropServices.RuntimeInformation','System.Threading.Thread']:
 p,pg=project();E.SubElement(pg,'GenFacadesOutputSourcePath').text=native(out/(name+'.Forwards.cs'));E.SubElement(pg,'LangVersion').text='preview'
 items=E.SubElement(p,'ItemGroup');E.SubElement(items,'ReferencePath',Include=native(core));E.SubElement(items,'ResolvedMatchingContract',Include=native(net10refs/(name+'.dll')))
 msbuild(name,p);dll=compile(name,[out/(name+'.Forwards.cs')],[core])
 contract=metadata(net10refs/(name+'.dll'),name+'-contract');actual=metadata(dll,name)
 expected=sorted(set(contract['publicTypes']+contract['forwards']))
 assert actual['forwards']==expected,(name,actual,expected)
 facades[name]=len(expected)
# Load each generated facade and resolve every forwarded type using the installed native CLR10.
probe=compile('ForwardProbe',[here/'inputs/ForwardProbe.cs'],[core],True)
layout=out/'CLR10 forwards λ';layout.mkdir()
for name in ['coreclr.dll','clrjit.dll','mscorrc.dll','clretwrc.dll']:shutil.copy2(Path('/clang64/lib/dotnet-bootstrap10/coreclr/10.0.5')/name,layout/name)
for name in ['System.Private.CoreLib.dll','corerun.exe']:shutil.copy2(Path('/clang64/lib/dotnet-bootstrap10/corelib/10.0.5')/name,layout/name)
shutil.copy2(probe,layout/probe.name)
for name in facades:shutil.copy2(out/(name+'.dll'),layout/(name+'.dll'))
win=lambda p:native(p).replace('/', '\\')
run([str(layout/'corerun.exe'),'-c',win(layout),win(layout/probe.name),*[win(layout/(n+'.dll')) for n in facades]],out/'forwarded-type-execution.log')
# Missing seed must fail rather than produce a silently incomplete facade.
p,pg=project();E.SubElement(pg,'GenFacadesOutputSourcePath').text=native(out/'missing.cs');items=E.SubElement(p,'ItemGroup');E.SubElement(items,'ReferencePath',Include=native(product/'tools/net/Microsoft.DotNet.GenFacades.dll'));E.SubElement(items,'ResolvedMatchingContract',Include=native(net10refs/'System.Threading.Thread.dll'))
msbuild('missing-seed',p,False)
assert 'Did not find type' in (out/'missing-seed.log').read_text()
# Original unsupported API generator, including exclusions and special Dispose behavior.
(out/'exclusions.txt').write_text('T:GenFacadesFixture.Excluded\n')
p=E.Element('Project');E.SubElement(p,'UsingTask',TaskName='NotSupportedAssemblyGenerator',AssemblyFile=native(product/'tools/net/Microsoft.DotNet.GenFacades.dll'))
items=E.SubElement(p,'ItemGroup');item=E.SubElement(items,'Source',Include=native(here/'inputs/Unsupported.cs'));E.SubElement(item,'OutputPath').text=native(out/'Unsupported.g.cs')
t=E.SubElement(p,'Target',Name='Generate');E.SubElement(t,'NotSupportedAssemblyGenerator',SourceFiles='@(Source)',Message='"source genfacades fixture"',LangVersion='preview',ApiExclusionListPath=native(out/'exclusions.txt'),RoslynAssembliesPath=native(product/'tools/net'))
msbuild('unsupported',p,target='Generate');assert 'class Excluded' not in (out/'Unsupported.g.cs').read_text()
probe=compile('UnsupportedProbe',[out/'Unsupported.g.cs',here/'inputs/UnsupportedProbe.cs'],sorted(refs.glob('*.dll')),True)
shutil.copy2(out/'Inspect.runtimeconfig.json',out/'UnsupportedProbe.runtimeconfig.json');run([dotnet,native(probe)],out/'unsupported-execution.log')
# Clear version seeds through the unchanged original MSBuild target/task.
clear=out/'clear.dll';shutil.copy2(out/'System.Threading.Thread.dll',clear)
p=E.Element('Project');E.SubElement(p,'UsingTask',TaskName='ClearAssemblyReferenceVersions',AssemblyFile=native(product/'tools/net/Microsoft.DotNet.GenFacades.dll'));t=E.SubElement(p,'Target',Name='Clear');E.SubElement(t,'ClearAssemblyReferenceVersions',Assembly=native(clear))
msbuild('clear-versions',p,target='Clear');before=metadata(out/'System.Threading.Thread.dll','clear-before');after=metadata(clear,'clear-after');assert any(r['version']!='0.0.0.0' for r in before['references']);assert all(r['version']=='0.0.0.0' for r in after['references']);assert before['forwards']==after['forwards']
record=dict(original_tasks_executed=['GenPartialFacadeSource','NotSupportedAssemblyGenerator','ClearAssemblyReferenceVersions'],real_net10_contract_facades=facades,real_net10_forwarders_verified=sum(facades.values()),missing_seed_rejected=True,all_generated_forwarders_resolved_on_installed_clr10=True,unsupported_api_execution_passed=True,clear_reference_versions_passed=True,installed_product_checked=len(sys.argv)>3,commands=commands,product_sha256={p.relative_to(product).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in product.rglob('*') if p.is_file()},full_original_tool_profiles_complete=False,full_dependency_goal_complete=False)
(out/'results.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS original GenFacades tasks:',len(facades),'real NET10 facades, strict missing-seed rejection, unsupported API execution and zero versions')
