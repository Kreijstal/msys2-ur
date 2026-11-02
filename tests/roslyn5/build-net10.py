"""Compile original NET10 VMR Common/CSharp/csc inputs against source NET10 refs."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,xml.etree.ElementTree as E
from functools import lru_cache

prepared=Path(sys.argv[1]).resolve();plan=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve()
assert not out.exists();out.mkdir();source=prepared/'roslyn-source'
@lru_cache(maxsize=None)
def native(p):
 value=str(p).replace('\\','/')
 if re.match(r'^/[a-zA-Z]/',value):return value[1].upper()+':'+value[2:]
 if value.startswith('/clang64/'):return native(Path('/clang64'))+value[len('/clang64'):]
 return subprocess.check_output(['cygpath','-am',value],text=True).strip()
source_native=native(source);prepared_native=native(prepared)
def local(value):
 value=value.replace('\\','/')
 if value.lower().startswith(source_native.lower()+'/'):return source/value[len(source_native)+1:]
 return Path(subprocess.check_output(['cygpath','-u',value],text=True).strip())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
model=json.loads((plan/'evaluated.json').read_text())
required={'Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp','csc'}
assert required<=set(model)<=required|{'Microsoft.CodeAnalysis.VisualBasic','vbc','VBCSCompiler'}
settings=E.parse(source/'eng/targets/Settings.props')
def public_key(name):
 value=settings.findtext('.//'+name);seen=set()
 while value and value.startswith('$('):
  assert value not in seen;seen.add(value);value=settings.findtext('.//'+value[2:-1])
 assert value and re.fullmatch('[0-9a-fA-F]+',value),(name,value)
 return value
key=public_key('MicrosoftSharedPublicKey');(out/'Roslyn.public.snk').write_bytes(bytes.fromhex(key))
assert hashlib.sha1(bytes.fromhex(key)).digest()[-8:][::-1].hex()=='31bf3856ad364e35'
dotnet='/clang64/lib/dotnet/dotnet.exe';compiler=Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap/CompilerHost.dll')
refs=sorted(Path('/clang64/lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
version='5.3.0-2.26113.113';commit='2333221c0564852ee5ceac9c622a0b14e864d76e'
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),
 DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
commands=[]
def run(command,log):
 with log.open('w') as f:r=subprocess.run(command,env=env,stdout=f,stderr=subprocess.STDOUT)
 commands.append(dict(command=command,log=str(log),exit_code=r.returncode))
 assert r.returncode==0,(r.returncode,log)
records={};binfolder=out/'bin';binfolder.mkdir()
for name in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp','csc']:
 print('Building original NET10 compiler project:',name,flush=True)
 entry=model[name];assert entry['properties']['TargetFramework']=='net10.0'
 folder=out/name;folder.mkdir();files=list(dict.fromkeys(local(i['full_path']) for i in entry['items']['Compile']))
 originals={p.relative_to(source).as_posix():sha(p) for p in files}
 if name=='Microsoft.CodeAnalysis.CSharp':
  files=[p for p in files if not p.is_relative_to(source/'src/Compilers/CSharp/Portable/Generated')]
  generated=sorted((prepared/'generated').glob('*.cs'));assert len(generated)==5
  files+=generated
 if name!='csc':
  resource_sources=sorted(p for p in (prepared/name).glob('*.Generated.cs') if p.name!='Friends.Generated.cs');assert resource_sources
  files+=resource_sources
 resources=[];resource_project=E.Element('Project');target=E.SubElement(resource_project,'Target',Name='Generate')
 # The original neutral strings are used by the generated source wrappers.
 for item in entry['items']['EmbeddedResource']:
  file=local(item['full_path']);assert file.is_file(),file
  metadata=item['metadata'];logical=metadata.get('LogicalName') or metadata.get('ManifestResourceName')
  if file.suffix=='.resx':
   logical=(logical or (metadata.get('Namespace') or name)+'.'+file.stem).removesuffix('.resources')+'.resources'
   output=folder/logical;E.SubElement(target,'GenerateResource',Sources=native(file),OutputResources=native(output),ExecuteAsTool='false');resources.append((output,logical))
  else:
   main=source/('src/Compilers/Core/Portable' if name=='Microsoft.CodeAnalysis' else 'src/Compilers/CSharp/Portable')
   logical=logical or name+'.'+file.relative_to(main).as_posix().replace('/','.')
   resources.append((file,logical))
 rp=folder/'Resources.proj';E.ElementTree(resource_project).write(rp,encoding='utf-8',xml_declaration=True)
 run([dotnet,'msbuild',native(rp),'-nologo','-t:Generate'],folder/'resources.log')
 attrs=['[assembly:System.Reflection.AssemblyVersion("5.3.0.0")]','[assembly:System.Reflection.AssemblyFileVersion("5.3.0.0")]',
  '[assembly:System.Reflection.AssemblyInformationalVersion("'+version+'+'+commit+'")]',
  '[assembly:System.Runtime.Versioning.TargetFramework(".NETCoreApp,Version=v10.0")]']
 for item in entry['items']['InternalsVisibleTo']:
  value=item['metadata'].get('Key','');pub=public_key(value[2:-1]) if value.startswith('$(') else value or key
  attrs.append('[assembly:System.Runtime.CompilerServices.InternalsVisibleTo('+json.dumps(item['identity']+', PublicKey='+pub)+')]')
 if name in {'Microsoft.CodeAnalysis.CSharp','csc'}:attrs.append('[assembly:Microsoft.CodeAnalysis.CommitHash("'+commit+'") ]')
 info=folder/'AssemblyInfo.g.cs';info.write_text('\n'.join(attrs)+'\n');files.append(info)
 defines=list(dict.fromkeys([d.strip() for d in re.split('[;,]',entry['properties']['DefineConstants']) if d.strip()]+['NET'+str(i)+'_0_OR_GREATER' for i in range(5,11)]+['NETCOREAPP'+s+'_OR_GREATER' for s in ['1_0','1_1','2_0','2_1','2_2','3_0','3_1']]))
 references=refs+[binfolder/(p+'.dll') for p in records]
 args=['/nostdlib+','/target:'+('exe' if name=='csc' else 'library'),'/langversion:preview','/nullable:enable','/unsafe+',
  '/optimize+','/deterministic+','/debug:portable','/publicsign+','/keyfile:"'+native(out/'Roslyn.public.snk')+'"',
  '/out:"'+native(binfolder/(name+'.dll'))+'"','/define:'+';'.join(defines),'/nowarn:CS0436;CS0618;SYSLIB0051;SYSLIB0050;RSEXPERIMENTAL005']
 if name=='csc':args+=['/main:Microsoft.CodeAnalysis.CSharp.CommandLine.Program']
 analyzers=[]
 if name=='Microsoft.CodeAnalysis':
  regex=Path('/clang64/lib/dotnet/generator-packs/runtime-10.0.5/analyzers/dotnet/cs/System.Text.RegularExpressions.Generator.dll')
  assert regex.is_file(),regex
  analyzers.append(regex)
  (folder/'generated').mkdir()
  args+=['/analyzer:"'+native(regex)+'"','/generatedfilesout:"'+native(folder/'generated')+'"']
 args+=['/reference:"'+native(p)+'"' for p in references]+['/resource:"'+native(p)+'",'+logical for p,logical in resources]+['"'+native(p)+'"' for p in files]
 rsp=folder/'compile.rsp';rsp.write_text('\n'.join(args)+'\n')
 run([dotnet,native(compiler),'-noconfig','@'+native(rsp)],folder/'compile.log')
 records[name]=dict(original_project_sources_sha256=originals,actual_compile_inputs_sha256={str(p):sha(p) for p in files},
  actual_analyzers_sha256={str(p):sha(p) for p in analyzers},generated_sources_sha256={str(p):sha(p) for p in (folder/'generated').rglob('*.cs')},
  actual_references_sha256={str(p):sha(p) for p in references},output_sha256=sha(binfolder/(name+'.dll')),
  original_profile='net10.0;DotNetBuildSourceOnly=true;DotNetBuildFromVMR=true',production_source_changes=0)
 (out/'build-status.json').write_text(json.dumps(records,indent=2)+'\n')
 print('PASS original NET10 compiler project:',name,flush=True)
(binfolder/'csc.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5'),configProperties={'System.GC.Server':True,'System.Runtime.TieredCompilation':False})),indent=2)+'\n')
target='.NETCoreApp,Version=v10.0';products={}
libraries={}
for name in records:
 package=name+'/'+version;products[package]=dict(runtime={name+'.dll':dict(assemblyVersion='5.3.0.0',fileVersion='5.3.0.0')})
 libraries[package]=dict(type='project',serviceable=False,sha512='')
products['csc/'+version]['dependencies']={'Microsoft.CodeAnalysis':version,'Microsoft.CodeAnalysis.CSharp':version}
products['Microsoft.CodeAnalysis.CSharp/'+version]['dependencies']={'Microsoft.CodeAnalysis':version}
(binfolder/'csc.deps.json').write_text(json.dumps(dict(runtimeTarget=dict(name=target,signature=''),compilationOptions={},targets={target:products},libraries=libraries),indent=2)+'\n')
(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
print('PASS original NET10 compiler compilation; satellites, complete metadata/source audit and execution still required')
