"""Compile the complete original NET10 framework graph using original build tasks."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys,xml.etree.ElementTree as E
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();only=sys.argv[3] if len(sys.argv)>3 else None
source=root/'r';evaluated=json.loads((out/'evaluated.json').read_text());projects=json.loads((out/'projects.json').read_text())
assert len(projects)==190 and set(evaluated)==set(projects)
here=Path(__file__).resolve().parent
native_root=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip();native_out=subprocess.check_output(['cygpath','-am',str(out)],text=True).strip()
path_cache={}
def native(path):
 path=Path(os.path.abspath(path))
 if path.is_relative_to(out):return native_out+'/'+path.relative_to(out).as_posix()
 if path.is_relative_to(root):return native_root+'/'+path.relative_to(root).as_posix()
 if str(path) not in path_cache:path_cache[str(path)]=subprocess.check_output(['cygpath','-am',str(path)],text=True).strip()
 return path_cache[str(path)]
def posix(value):
 value=value.replace('\\','/')
 for n,p in [(native_out,out),(native_root,root)]:
  if value.lower().startswith(n.lower()+'/'):return p/value[len(n)+1:]
 return Path(subprocess.check_output(['cygpath','-u',value],text=True).strip())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
dotnet='/clang64/lib/dotnet/dotnet.exe';compiler=Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap/CompilerHost.dll');refs=Path('/clang64/lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0');corelib=Path('/clang64/lib/dotnet-bootstrap10/corelib/10.0.5/System.Private.CoreLib.dll')
generators=Path('/clang64/lib/dotnet/generator-packs/runtime-10.0.5/analyzers/dotnet/cs')
product=out/'lib';product.mkdir(exist_ok=True);stubs=out/'stubs';stubs.mkdir(exist_ok=True)
byproject={native(source/p['project']).lower():n for n,p in projects.items()};dependencies={};analyzers={}
for name,entry in evaluated.items():
 ds=[];gs=[]
 for item in entry['items']['ProjectReference']:
  path=item['full_path'].replace('\\','/');base=Path(path).stem
  if item['metadata'].get('OutputItemType')=='Analyzer':gs.append(base);continue
  if item['metadata'].get('ReferenceOutputAssembly','').lower()=='false':continue
  dep='System.Private.CoreLib' if base=='System.Private.CoreLib' else byproject.get(path.lower())
  assert dep,(name,'Unresolved original project reference',item)
  if dep!=name and dep not in ds:ds.append(dep)
 if projects[name]['kind']=='stub' and 'System.Runtime' not in ds:ds.append('System.Runtime')
 dependencies[name]=ds;analyzers[name]=list(dict.fromkeys(gs))
order=[];seen=set()
def visit(name,stack=()):
 if name=='System.Private.CoreLib' or name in seen:return
 assert name not in stack,('Cycle',stack,name)
 for dep in dependencies[name]:visit(dep,stack+(name,))
 seen.add(name);order.append(name)
for name in ([only] if only else sorted(projects)):visit(name)
(out/'build-order.json').write_text(json.dumps(dict(order=order,dependencies=dependencies,analyzers=analyzers),indent=2)+'\n')
def binary(name):return corelib if name=='System.Private.CoreLib' else (stubs if projects[name]['kind']=='stub' else product)/(name.removeprefix('stub:')+'.dll')
keys=out/'keys';keys.mkdir(exist_ok=True)
for item in E.parse(out/'tools/StrongName.props').iter():
 if item.tag.endswith('PublicKey') and item.text and re.fullmatch('[0-9a-fA-F]+',item.text.strip()):
  (keys/(item.tag.removesuffix('PublicKey')+'.pubkey')).write_bytes(bytes.fromhex(item.text.strip()))
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
def run(cmd,log):
 with log.open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env)
 assert r.returncode==0,(r.returncode,log,cmd)
def query(cmd,log):
 r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,env=env);log.write_text(r.stdout);assert r.returncode==0,(r.returncode,log)
 decoder=json.JSONDecoder()
 for match in re.finditer(r'(?m)^\s*\{',r.stdout):
  try:value,end=decoder.raw_decode(r.stdout[match.start():].lstrip())
  except json.JSONDecodeError:continue
  if isinstance(value,dict) and 'Items' in value and 'Properties' in value:return value
 raise AssertionError(('No compiler input JSON',log))
statusfile=out/'build-status.json';status=json.loads(statusfile.read_text()) if statusfile.exists() else {}
for name in order:
 assembly=name.removeprefix('stub:');entry=evaluated[name];props=entry['properties'];kind=projects[name]['kind'];folder=out/'steps'/name.replace(':','-');folder.mkdir(parents=True,exist_ok=True)
 if name in status and status[name].get('complete') and binary(name).is_file() and status[name]['output_sha256']==sha(binary(name)):
  print('Previously verified output:',name,flush=True);continue
 print('Building original framework project:',name,flush=True)
 closure=set()
 def include(n):
  for d in dependencies.get(n,[]):
   if d not in closure:closure.add(d);include(d)
 include(name)
 references=[binary(n) for n in ['System.Private.CoreLib',*order] if n in closure]
 assert all(p.is_file() for p in references),(name,'Missing dependency outputs',references)
 # Original Reference items name reference assemblies; implementation ProjectReferences remain implementation inputs.
 for item in entry['items']['Reference']:
  path=refs/(Path(item['identity']).stem+'.dll');assert path.is_file(),(name,item);references.append(path)
 references=list(dict.fromkeys(references))
 p=E.Element('Project');E.SubElement(p,'Import',Project=native(out/'p'/name.replace(':','-')/Path(projects[name]['project']).name))
 pg=E.SubElement(p,'PropertyGroup');obj=out/'p'/name.replace(':','-')/'obj';obj.mkdir(exist_ok=True)
 values=dict(IntermediateOutputPath=native(obj)+'/',ArcadeSdkBuildTasksAssembly=native(out/'tools/Framework10.Arcade.Resources/bin/Release/net8.0/Framework10.Arcade.Resources.dll'),ILLinkTasksAssembly=native(out/'tools/net/ILLink.Tasks.dll'),GenFacadesRoslynAssembliesPath=native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')),GenFacadesOutputSourcePath=native(obj/'Forwards.g.cs'),AssemblyVersion=props['AssemblyVersion'] or props['MajorVersion']+'.0.0.0',FileVersion=(root/'file-version.txt').read_text().strip(),ILLinkTrimAssemblyPath=native(obj/(assembly+'.dll')),ILLinkTrimAssemblySymbols=native(obj/(assembly+'.pdb')),ILLinkTrimInputPath=native(obj/'PreTrim')+'/',ILLinkTrimOutputPath=native(obj)+'/',TargetName=assembly,TargetExt='.dll')
 for k,v in values.items():E.SubElement(pg,k).text=v
 ig=E.SubElement(p,'ItemGroup')
 for file in references:
  for itemkind in ['ReferencePath','ReferencePathWithRefAssemblies']:E.SubElement(ig,itemkind,Include=native(file))
 if props['IsPartialFacadeAssembly']=='true':E.SubElement(ig,'ResolvedMatchingContract',Include=native(refs/(assembly+'.dll')))
 generation_inputs=[]
 if props['GeneratePlatformNotSupportedAssemblyMessage']:
  contract=(source/projects[name]['project']).parent.parent/'ref'/(assembly+'.csproj')
  assert contract.is_file(),contract
  generation_inputs.append(contract)
  for item in E.parse(contract).findall('.//Compile'):
   identity=item.get('Include');assert identity and not any(c in identity for c in '$@%*;'),identity
   file=contract.parent/identity;assert file.is_file(),file
   generation_inputs.append(file)
   generated=E.SubElement(ig,'GenFacadeNotSupportedCompileInput',Include=native(file))
   E.SubElement(generated,'OutputPath').text=native(obj/(file.stem+'.notsupported.cs'))
 E.SubElement(p,'Import',Project=native(out/'tools/GenerateResxSource.targets'))
 E.SubElement(p,'Import',Project=native(Path('/clang64/lib/dotnet/tool-packs/genfacades-10.0.5-bootstrap/build/Microsoft.DotNet.GenFacades.targets')))
 # Reference resolution is supplied explicitly from the audited original dependency graph.
 E.SubElement(p,'Target',Name='ResolveReferences');E.SubElement(p,'Target',Name='ResolveMatchingContract')
 if generation_inputs:
  # Supply the original contract project's explicit source items, replacing
  # only project-output resolution. The original unsupported target/task runs.
  E.SubElement(p,'Target',Name='_GetGenFacadeNotSupportedCompileInputs')
 if assembly=='System.Diagnostics.DiagnosticSource':
  E.SubElement(p,'UsingTask',TaskName='GenerateFileFromTemplate',AssemblyFile=native(out/'tools/Templating/bin/Release/net8.0/Microsoft.DotNet.Build.Tasks.Templating.dll'))
  for original_target in E.parse(source/projects[name]['project']).getroot().findall('Target'):
   if original_target.get('Name')=='_GenerateThisAssemblyInfo':
    # The task and original target are kept; only relative template inputs are rebound.
    for task in original_target.iter():
     if task.get('TemplateFile'):task.set('TemplateFile',native((source/projects[name]['project']).parent/task.get('TemplateFile')))
    p.append(original_target)
 targets=['_GenerateResxSource','_EmbedILLinkXmls','CalculateIncludeDllSafeSearchPathAttribute']
 if assembly=='System.Diagnostics.DiagnosticSource':targets.append('_GenerateThisAssemblyInfo')
 if kind=='stub':targets.append('CreateCompileSourceForForwardedTypes')
 if props['IsPartialFacadeAssembly']=='true':targets.append('GeneratePartialFacadeSource')
 if generation_inputs:targets.append('AddGenFacadeNotSupportedCompileItem')
 E.SubElement(p,'Target',Name='PrepareOriginal',DependsOnTargets=';'.join(targets))
 path=folder/Path(projects[name]['project']).name;E.indent(p);E.ElementTree(p).write(path,encoding='utf-8',xml_declaration=True)
 inner_tfm=props['TargetFramework'] or 'net10.0'
 data=query([dotnet,'msbuild',native(path),'-p:TargetFramework='+inner_tfm,'-nologo','-t:PrepareOriginal','-getItem:Compile,EmbeddedResource,AssemblyAttribute','-getProperty:AssemblyName,AssemblyVersion,MajorVersion,DefineConstants,NoWarn,Nullable,RootNamespace,GenFacadesForceZeroVersionSeeds,ILLinkTrimAssembly,TargetFramework,AllowUnsafeBlocks,OptionStrict,OptionExplicit,OptionInfer,RemoveIntegerChecks'],folder/'prepare.log')
 (folder/'actual-inputs.json').write_text(json.dumps(data,indent=2)+'\n')
 def itempath(item):
  value=item['Identity'].replace('\\','/')
  return posix(item['FullPath']) if value.startswith('/') or (len(value)>1 and value[1]==':') else (source/projects[name]['project']).parent/value
 cs=list(dict.fromkeys(itempath(i) for i in data['Items']['Compile']));assert cs and all(f.is_file() for f in cs),(name,cs)
 # Generate binary resources with the SDK's original GenerateResource task.
 resource_project=E.Element('Project');resource_target=E.SubElement(resource_project,'Target',Name='Generate');resources=[]
 for item in data['Items']['EmbeddedResource']:
  sourcefile=itempath(item);assert sourcefile.is_file(),sourcefile
  logical=item.get('LogicalName') or item.get('ManifestResourceName') or assembly+'.'+sourcefile.name
  if sourcefile.suffix=='.resx':
   logical=logical.removesuffix('.resources')+'.resources';file=obj/logical
   E.SubElement(resource_target,'GenerateResource',Sources=native(sourcefile),OutputResources=native(file),ExecuteAsTool='false');resources.append((file,logical))
  else:resources.append((sourcefile,logical))
 rp=folder/'Resources.proj';E.ElementTree(resource_project).write(rp,encoding='utf-8',xml_declaration=True);run([dotnet,'msbuild',native(rp),'-nologo','-t:Generate','-v:minimal'],folder/'resources.log')
 pp=data['Properties'];version=pp['AssemblyVersion'] or pp['MajorVersion']+'.0.0.0';major=pp['MajorVersion'];fileversion=(root/'file-version.txt').read_text().strip()
 if major!='10':
  versionproj=E.Element('Project');E.SubElement(versionproj,'UsingTask',TaskName='Microsoft.DotNet.Arcade.Sdk.CalculateAssemblyAndFileVersions',AssemblyFile=native(root/'version-build/bin/Release/net8.0/RuntimeServicing.VersionBuildTasks.dll'));t=E.SubElement(versionproj,'Target',Name='Calculate');call=E.SubElement(t,'Microsoft.DotNet.Arcade.Sdk.CalculateAssemblyAndFileVersions',VersionPrefix=major+'.0.5',BuildNumber='20260218.0');E.SubElement(call,'Output',TaskParameter='FileVersion',PropertyName='FV');E.SubElement(t,'WriteLinesToFile',File=native(folder/'fv.txt'),Lines='$(FV)',Overwrite='true');vp=folder/'Version.proj';E.ElementTree(versionproj).write(vp,encoding='utf-8');run([dotnet,'msbuild',native(vp),'-nologo','-t:Calculate'],folder/'version.log');fileversion=(folder/'fv.txt').read_text(encoding='utf-8-sig').strip()
 info=obj/('AssemblyInfo.g.vb' if kind=='vb' else 'AssemblyInfo.g.cs')
 attribute_project=E.Element('Project');ig=E.SubElement(attribute_project,'ItemGroup')
 records=[dict(Identity='System.Reflection.AssemblyVersion',_Parameter1=version),dict(Identity='System.Reflection.AssemblyFileVersion',_Parameter1=fileversion),dict(Identity='System.Reflection.AssemblyInformationalVersion',_Parameter1='10.0.5+081d220c0a773ffb7c6bea6b48727833576a65ef'),dict(Identity='System.Runtime.Versioning.TargetFramework',_Parameter1='.NETCoreApp,Version=v10.0')]+data['Items']['AssemblyAttribute']
 for item in records:
  attribute=E.SubElement(ig,'GeneratedAttribute',Include=item['Identity'])
  for key,value in item.items():
   if key.startswith('_Parameter'):E.SubElement(attribute,key).text=value
 t=E.SubElement(attribute_project,'Target',Name='Generate');E.SubElement(t,'WriteCodeFragment',Language='VB' if kind=='vb' else 'C#',AssemblyAttributes='@(GeneratedAttribute)',OutputFile=native(info))
 ap=folder/'AssemblyAttributes.proj';E.indent(attribute_project);E.ElementTree(attribute_project).write(ap,encoding='utf-8',xml_declaration=True);run([dotnet,'msbuild',native(ap),'-nologo','-t:Generate','-v:minimal'],folder/'attributes.log');cs.append(info)
 defines=list(dict.fromkeys([d.strip() for d in re.split('[;,]',pp['DefineConstants']) if d.strip()]+['TRACE','RELEASE','NET','NETCOREAPP','NET10_0',*['NET'+str(n)+'_0_OR_GREATER' for n in range(5,11)],*['NETCOREAPP'+n+'_OR_GREATER' for n in ['1_0','1_1','2_0','2_1','2_2','3_0','3_1']]]))
 if '-windows' in props['TargetFramework']:defines+=['WINDOWS','WINDOWS7_0_OR_GREATER']
 key=keys/(props['StrongNameKeyId']+'.pubkey');assert key.is_file(),(name,key)
 args=['/nostdlib+','/target:library','/optimize+','/deterministic+','/unsafe+','/nullable:'+('enable' if not pp['Nullable'] else pp['Nullable']),'/debug:portable','/langversion:preview','/runtimemetadataversion:v4.0.30319','/publicsign+','/keyfile:"'+native(key)+'"','/out:"'+native(obj/(assembly+'.dll'))+'"','/define:'+';'.join(defines),'/nowarn:'+pp['NoWarn'],'/generatedfilesout:"'+native(obj/'generated')+'"']
 (obj/'generated').mkdir(exist_ok=True)
 args+=['/reference:"'+native(f)+'"' for f in references]
 args+=['/resource:"'+native(f)+'",'+logical for f,logical in resources]
 config=obj/'build.globalconfig';config.write_text('is_global = true\nbuild_property.TargetFrameworkIdentifier = .NETCoreApp\nbuild_property.TargetFrameworkVersion = v10.0\nbuild_property.LibraryImportGenerator_UseMarshalType = true\n');args.append('/analyzerconfig:"'+native(config)+'"')
 names={'LibraryImportGenerator':'Microsoft.Interop.LibraryImportGenerator','ComInterfaceGenerator':'Microsoft.Interop.ComInterfaceGenerator','JSImportGenerator':'Microsoft.Interop.JavaScript.JSImportGenerator'}
 for g in analyzers[name]:
  file=generators/(names.get(g,g)+'.dll');assert file.is_file(),(name,g,file);args.append('/analyzer:"'+native(file)+'"')
 for item in entry['items']['AdditionalFiles']:args.append('/additionalfile:"'+item['full_path']+'"')
 if kind=='vb':
  args=['/nostdlib','/target:library','/optimize+','/deterministic','/debug:portable','/vbruntime-','/optionstrict+','/optionexplicit+','/optioninfer-','/optioncompare:binary','/removeintchecks-','/langversion:latest','/publicsign','/keyfile:"'+native(key)+'"','/out:"'+native(obj/(assembly+'.dll'))+'"',*(['/rootnamespace:'+pp['RootNamespace']] if pp['RootNamespace'] else []),'/define:'+','.join(d if '=' in d else d+'=True' for d in defines if d)+',_MYTYPE="Empty"','/imports:Microsoft.VisualBasic,System,System.Collections,System.Collections.Generic,System.Diagnostics,System.Linq,System.Threading.Tasks']
  args+=['/reference:"'+native(f)+'"' for f in references]+['/resource:"'+native(f)+'",'+logical for f,logical in resources]
 args+=['"'+native(f)+'"' for f in cs];rsp=folder/'compile.rsp';rsp.write_text('\n'.join(args)+'\n')
 selected_compiler=Path('/clang64/lib/dotnet/compiler-packs/roslyn-vb-4.9.2/vbc.dll') if kind=='vb' else compiler
 assert selected_compiler.is_file(),selected_compiler
 run([dotnet,native(selected_compiler),'-noconfig','@'+native(rsp)],folder/'compile.log')
 # Apply original zero-version and library-link policies after compilation.
 post=[]
 if pp['GenFacadesForceZeroVersionSeeds']=='true':post.append('ClearAssemblyReferenceVersions')
 if pp['ILLinkTrimAssembly']=='true':post.append('ILLinkTrimAssembly')
 if post:run([dotnet,'msbuild',native(path),'-p:TargetFramework='+inner_tfm,'-nologo','-t:'+';'.join(post),'-v:minimal'],folder/'postcompile.log')
 shutil.copy2(obj/(assembly+'.dll'),binary(name))
 if (obj/(assembly+'.pdb')).is_file():shutil.copy2(obj/(assembly+'.pdb'),binary(name).with_suffix('.pdb'))
 status[name]=dict(complete=True,kind=kind,assembly_version=version,file_version=fileversion,original_cs_items=len(cs)-1,resources=len(resources),analyzers=analyzers[name],reference_sha256={str(f):sha(f) for f in references},compiled_sources_sha256={str(f):sha(f) for f in cs},generation_inputs_sha256={str(f):sha(f) for f in generation_inputs},output_sha256=sha(binary(name)),original_library_policy_applied=pp['ILLinkTrimAssembly']=='true',full_framework_complete=False)
 statusfile.write_text(json.dumps(status,indent=2)+'\n');print('PASS framework assembly:',name,flush=True)
if not only:
 assert len(status)==len(projects),'Complete original graph has pending projects'
 print('PASS complete original implementation compilation; packaging/runtime gates remain required')
else:print('PASS requested original project and its full dependency closure:',only)
