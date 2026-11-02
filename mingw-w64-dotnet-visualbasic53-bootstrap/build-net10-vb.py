"""Compile the original VMR NET10 VisualBasic project with freshly generated VB."""
from pathlib import Path
from functools import lru_cache
import hashlib,json,os,re,subprocess,sys,xml.etree.ElementTree as E
source,plan,common,generators,out=(Path(p).resolve() for p in sys.argv[1:6]);assert not out.exists();out.mkdir()
@lru_cache(maxsize=None)
def native(p):
 s=str(p).replace('\\','/')
 if re.match(r'^/[a-zA-Z]/',s):return s[1].upper()+':'+s[2:]
 if s.startswith('/clang64/'):return native(Path('/clang64'))+s[len('/clang64'):]
 return subprocess.check_output(['cygpath','-am',s],text=True).strip()
source_native=native(source)
def local(s):
 s=s.replace('\\','/');assert s.lower().startswith(source_native.lower()+'/'),s
 return source/s[len(source_native)+1:]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
entry=json.loads((plan/'evaluated.json').read_text())['Microsoft.CodeAnalysis.VisualBasic']
assert entry['properties']['TargetFramework']=='net10.0'
selected=list(dict.fromkeys(local(i['full_path']) for i in entry['items']['Compile']));assert len(selected)==915
main=source/'src/Compilers/VisualBasic/Portable';files=[p for p in selected if not p.is_relative_to(main/'Generated')]
generated=sorted((generators/'generated').glob('*.vb'));assert len(generated)==5;files+=generated
resx=main/'VBResources.resx';logical='Microsoft.CodeAnalysis.VisualBasic.VBResources'
code=['Namespace Microsoft.CodeAnalysis.VisualBasic','Friend NotInheritable Class VBResources','Private Sub New()','End Sub','Private Shared ReadOnly Manager As New Global.System.Resources.ResourceManager("'+logical+'", GetType(VBResources).Assembly)','Friend Shared ReadOnly Property ResourceManager As Global.System.Resources.ResourceManager','Get','Return Manager','End Get','End Property','Friend Shared Property Culture As Global.System.Globalization.CultureInfo']
for i in E.parse(resx).iter('data'):
 n=i.get('name');assert n.isidentifier(),n
 code+=['Friend Shared ReadOnly Property ['+n+'] As String','Get','Return Manager.GetString("'+n+'", Culture)','End Get','End Property']
code+=['End Class','End Namespace'];wrapper=out/'VBResources.g.vb';wrapper.write_text('\n'.join(code)+'\n');files.append(wrapper)
settings=E.parse(source/'eng/targets/Settings.props')
def keyvalue(n):
 value=settings.findtext('.//'+n)
 while value and value.startswith('$('):value=settings.findtext('.//'+value[2:-1])
 assert value and re.fullmatch('[0-9a-fA-F]+',value),n
 return value
key=keyvalue('MicrosoftSharedPublicKey');(out/'Roslyn.public.snk').write_bytes(bytes.fromhex(key))
attrs=['<Assembly: Global.System.Reflection.AssemblyVersion("5.3.0.0")>','<Assembly: Global.System.Reflection.AssemblyFileVersion("5.3.0.0")>','<Assembly: Global.System.Reflection.AssemblyInformationalVersion("5.3.0-2.26113.113+2333221c0564852ee5ceac9c622a0b14e864d76e")>','<Assembly: Global.System.Runtime.Versioning.TargetFramework(".NETCoreApp,Version=v10.0")>','<Assembly: Global.Microsoft.CodeAnalysis.CommitHash("2333221c0564852ee5ceac9c622a0b14e864d76e")>']
for i in entry['items']['InternalsVisibleTo']:
 pub=i['metadata'].get('Key') or key
 if pub.startswith('$('):pub=keyvalue(pub[2:-1])
 attrs.append('<Assembly: Global.System.Runtime.CompilerServices.InternalsVisibleTo('+json.dumps(i['identity']+', PublicKey='+pub)+')>')
info=out/'AssemblyInfo.g.vb';info.write_text('\n'.join(attrs)+'\n');files.append(info)
resource_project=E.Element('Project');target=E.SubElement(resource_project,'Target',Name='Generate');resources=[]
for i in entry['items']['EmbeddedResource']:
 p=local(i['full_path'])
 if p.suffix=='.resx':
  output=out/'VBResources.resources';E.SubElement(target,'GenerateResource',Sources=native(p),OutputResources=native(output),ExecuteAsTool='false');resources.append((output,logical+'.resources'))
 else:resources.append((p,p.name))
rp=out/'Resources.proj';E.ElementTree(resource_project).write(rp,encoding='utf-8',xml_declaration=True)
host='/clang64/lib/dotnet/dotnet.exe';env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')))
commands=[]
def run(command,label):
 with (out/(label+'.log')).open('w') as f:r=subprocess.run(command,env=env,stdout=f,stderr=subprocess.STDOUT)
 commands.append(dict(command=command,exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
run([host,'msbuild',native(rp),'-nologo','-t:Generate'],'resources')
refs=sorted(p for p in Path('/clang64/lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll') if p.stem not in {'Microsoft.VisualBasic','Microsoft.VisualBasic.Core'});assert len(refs)==165
refs.append(common/'bin/Microsoft.CodeAnalysis.dll')
defines=[d for d in re.split('[;,]',entry['properties']['DefineConstants']) if d]+['NET'+str(i)+'_0_OR_GREATER' for i in range(5,11)]
imports=[i['identity'].replace(' = ','=') for i in entry['items']['Import']]
args=['/nostdlib','/nosdkpath','/target:library','/optimize+','/deterministic','/debug:portable','/vbruntime*','/optionstrict+','/optionexplicit+','/optioninfer+','/optioncompare:binary','/removeintchecks+','/langversion:latest','/publicsign','/keyfile:"'+native(out/'Roslyn.public.snk')+'"','/out:"'+native(out/'Microsoft.CodeAnalysis.VisualBasic.dll')+'"','/define:'+','.join(dict.fromkeys(d if '=' in d else d+'=True' for d in defines))+',_MYTYPE="Empty"','/imports:'+','.join(imports),'/nowarn:40057,42014']
args+=['/reference:"'+native(p)+'"' for p in refs]+['/resource:"'+native(p)+'",'+n for p,n in resources]+['"'+native(p)+'"' for p in files]
rsp=out/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');compiler=Path('/clang64/lib/dotnet/compiler-packs/roslyn-vb-4.9.2/vbc.dll')
run([host,native(compiler),'-noconfig','@'+native(rsp)],'compile')
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_project_source_hashes={p.relative_to(source).as_posix():sha(p) for p in selected},actual_compile_input_hashes={str(p):sha(p) for p in files},actual_reference_hashes={str(p):sha(p) for p in refs},resource_inputs_sha256={p.relative_to(source).as_posix():sha(p) for p in [resx,*[p for p,n in resources if p.is_relative_to(source)]]},compiler_sha256=sha(compiler),output_sha256=sha(out/'Microsoft.CodeAnalysis.VisualBasic.dll'),original_target='net10.0',original_production_source_changes=0,original_generated_vb_sources=5,execution_verified=False,all_localized_satellites_built=False,formal_package_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original NET10 VB compiler compilation:915 original inputs,5 freshly generated files; execution/localization still required')
