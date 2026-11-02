"""Build all five original CodePages4.5.1 implementations from both source lineages."""
from pathlib import Path
import functools,hashlib,json,os,posixpath,shutil,subprocess,sys,tarfile,xml.etree.ElementTree as E,zipfile
old,new,out,compiler=(Path(s).resolve() for s in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();library='System.Text.Encoding.CodePages'
lineages={};commands=[];results={};specs=[('legacy',old,'4d1af962ca0fede10beb01d197367c2f90e92c97','1782b55a84ae89baa4fcb5c8400c3d7042c5c617a4e35ce1b0ad16952d6981b2'),('current',new,'99ce22c306b07f99ddae60f443d23a983ae78f7b','87d9ed6638b66ed119df9c8923df0fec0b5467819371f297c474f23bb1ff204a')]
for tag,archive,commit,h in specs:
 assert sha(archive)==h;source=out/'sources'/tag;source.mkdir(parents=True);hashes={}
 with tarfile.open(archive) as t:
  assert t.pax_headers['comment']==commit
  prefix=t.getmembers()[0].name.split('/')[0];original_xml=E.fromstring(t.extractfile(prefix+'/src/'+library+'/src/'+library+'.csproj').read());common={'src/Common/src/System/SR.cs'}
  for entry in original_xml.findall('.//{*}Compile'):
   include=entry.get('Include')
   if '$(CommonPath)' in include:common.add(posixpath.normpath(posixpath.join('src/'+library+'/src',include.replace('$(CommonPath)','../../Common/src').replace('\\','/'))))
  for m in t:
   n=m.name.partition('/')[2]
   if not m.isfile() or not (n.startswith('src/'+library+'/') or n in common or n in {'dir.props','dir.targets','src/dir.props','src/dir.targets','LICENSE','THIRD-PARTY-NOTICES','LICENSE.TXT','THIRD-PARTY-NOTICES.TXT','Packaging.props','pkg/useSharedDesignerContext.txt'}):continue
   b=t.extractfile(m).read();assert '..' not in Path(n).parts and not n.lower().endswith(('.dll','.exe','.pdb','.nupkg')) and b[:2]!=b'MZ';p=source/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);hashes[n]=sha(p)
 lineages[tag]=dict(commit=commit,archive_sha256=h,original_file_sha256=hashes)
native=functools.lru_cache(None)(lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip());metadata=json.loads((here/'original-profile-requirements-20261031.json').read_text());policy=json.loads((here/'inputs/published-native-resources.json').read_text(encoding='utf-8-sig'));matrix=json.loads((here/'inputs/source-contract-build-matrix.json').read_text())
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1');config=out/'NuGet.config';config.write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
def run(label,cmd,cwd=None):
 with (out/(label+'.log')).open('w') as log:r=subprocess.run(cmd,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(label,(out/(label+'.log')).read_text(errors='replace')[-8000:])
for profile,spec in metadata['profiles'].items():
 legacy=profile.startswith('legacy');windows=profile.endswith('windows');tag='legacy' if legacy else 'current';source=out/'sources'/tag;folder=out/'profiles'/profile;folder.mkdir(parents=True);original=source/'src'/library/'src'/(library+'.csproj');project=E.parse(original)
 tfm='netstandard1.3' if legacy else 'netcoreapp2.0' if profile=='netcore2-windows' else 'netstandard2.0';group='' if legacy else 'netcoreapp2.0' if profile=='netcore2-windows' else 'netstandard';selected=[]
 for ig in project.findall('{*}ItemGroup'):
  condition=ig.get('Condition','').strip()
  if not ig.findall('{*}Compile'):continue
  assert condition in ['',"'$(TargetsWindows)' == 'true'","'$(TargetsUnix)' == 'true'","'$(TargetGroup)' == 'netstandard' AND '$(TargetsWindows)' != 'true'"],condition
  if condition=="'$(TargetsWindows)' == 'true'" and not windows:continue
  if condition=="'$(TargetsUnix)' == 'true'" and windows:continue
  if condition=="'$(TargetGroup)' == 'netstandard' AND '$(TargetsWindows)' != 'true'" and (windows or group!='netstandard'):continue
  for c in ig.findall('{*}Compile'):selected.append((original.parent/c.get('Include').replace('$(CommonPath)','../../Common/src').replace('\\','/')).resolve())
 selected.append(source/'src/Common/src/System/SR.cs');assert all(p.is_file() for p in selected)
 alias=spec['original_paths'][0];baseline=json.loads((here/'inputs'/(alias.replace('/','_')+'.json')).read_text())[library+'.dll'];refs=[];dependency=None
 if legacy:
  rootdeps=json.loads((original.parent/'project.json').read_text())['dependencies'];closure=set()
  def select(key):
   if key in closure:return
   assert key in matrix,key;closure.add(key)
   for r in matrix[key]['references']:
    name,version=r.split(', Version=');select(name+'/'+version.split(',')[0])
  for name,version in rootdeps.items():
   if name=='Microsoft.NETCore.Platforms':continue
   select(name+'/'+version+'.0')
  highest={}
  for key in closure:
   name,v=key.split('/')
   if name not in highest or tuple(map(int,v.split('.')))>tuple(map(int,highest[name].split('/')[1].split('.'))):highest[name]=key
  contracts=Path('/clang64/lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts');refs=[contracts/key/(key.split('/')[0]+'.dll') for key in sorted(highest.values())]
 else:
  refs=sorted(Path('/clang64/lib/dotnet/reference-packs/netcore20-contracts-bootstrap/ref').glob('*.dll')) if tfm=='netcoreapp2.0' else sorted(Path('/clang64/lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll'))
  assert len(refs)==(10 if tfm=='netcoreapp2.0' else 113)
  package=Path('/clang64/lib/dotnet/library-packs/system.runtime.compilerservices.unsafe.4.5.2.nupkg');file=folder/'source-dependencies/System.Runtime.CompilerServices.Unsafe.dll';file.parent.mkdir()
  with zipfile.ZipFile(package) as z:file.write_bytes(z.read('ref/netstandard2.0/System.Runtime.CompilerServices.Unsafe.dll'))
  refs.append(file);dependency=dict(package=package.name,package_sha256=sha(package),asset='ref/netstandard2.0/System.Runtime.CompilerServices.Unsafe.dll',DLL_sha256=sha(file))
 assert refs and all(p.is_file() for p in refs)
 info=['[assembly:System.Reflection.AssemblyVersion('+json.dumps(baseline['identity'].split('Version=')[1].split(',')[0])+')]']
 for a in baseline['attributes']:
  name=a['type']
  if name.startswith('System.Reflection.') or name in ['System.CLSCompliantAttribute','System.Resources.NeutralResourcesLanguageAttribute','System.Security.AllowPartiallyTrustedCallersAttribute']:
   values=[v.lower() if name=='System.CLSCompliantAttribute' else json.dumps(v) for v in a['arguments']];info.append('[assembly:'+name+'('+','.join(values)+')]')
  elif name=='System.Runtime.InteropServices.DefaultDllImportSearchPathsAttribute':info.append('[assembly:'+name+'((System.Runtime.InteropServices.DllImportSearchPath)'+a['arguments'][0]+')]')
 (folder/'Version.cs').write_text('\n'.join(info)+'\n');v=policy[alias]['native']
 rc=['LANGUAGE 0,0','1 VERSIONINFO','FILEVERSION '+','.join(str(v['File'+n+'Part']) for n in ['Major','Minor','Build','Private']),'PRODUCTVERSION '+','.join(str(v['Product'+n+'Part']) for n in ['Major','Minor','Build','Private']),'FILEFLAGSMASK 0x3f','FILEFLAGS 0','FILEOS 4','FILETYPE 2','FILESUBTYPE 0','BEGIN','BLOCK "StringFileInfo"','BEGIN','BLOCK "000004b0"','BEGIN']
 for k in ['CompanyName','FileDescription','FileVersion','InternalName','LegalCopyright','OriginalFilename','ProductVersion','ProductName','Comments','LegalTrademarks','PrivateBuild','SpecialBuild']:rc.append('VALUE '+json.dumps(k)+', L'+json.dumps(v[k],ensure_ascii=True).replace('\\u','\\x'))
 rc+=['END','END','BLOCK "VarFileInfo"','BEGIN','VALUE "Translation", 0, 1200','END','END'];(folder/'version.rc').write_text('\n'.join(rc)+'\n');run('rc-'+profile,['/clang64/bin/llvm-rc.exe','-fo','version.res','version.rc'],folder)
 p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup');props=dict(TargetFramework=tfm,DisableImplicitFrameworkReferences='true',NoStdLib='true',NoConfig='true',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',CheckEolTargetFramework='false',UseAppHost='false',GenerateAssemblyInfo='false',GenerateTargetFrameworkAttribute='false',AssemblyName=library,RootNamespace=library,TargetGroup=group,TargetsWindows=str(windows).lower(),TargetsUnix=str(not windows).lower(),AllowUnsafeBlocks='true',LangVersion='6' if legacy else '7.3',WarningLevel='4',NoWarn='1701;1702',TreatWarningsAsErrors='true',Nullable='disable',SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile=native(here/'inputs/Microsoft.snk'),Win32Resource=native(folder/'version.res'),CscToolPath=native(compiler),CscToolExe='csc44.cmd',UseSharedCompilation='false',DebugType='portable',Optimize='true',DefineConstants='TRACE',AppendTargetFrameworkToOutputPath='false',AppendRuntimeIdentifierToOutputPath='false',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false')
 for k,v in props.items():E.SubElement(pg,k).text=v
 ig=E.SubElement(p,'ItemGroup')
 for f in selected+[folder/'Version.cs']:E.SubElement(ig,'Compile',Include=native(f))
 for f in refs:E.SubElement(ig,'Reference',Include=f.stem,HintPath=native(f),Private='false')
 resx=original.parent/'Resources/Strings.resx';logical='FxResources.'+library+'.SR';values={e.get('name'):e.findtext('value') for e in E.parse(resx).findall('data')}
 code=['namespace FxResources.'+library+' {internal static class SR {}}','namespace System {internal partial class SR {private static System.Type ResourceType {get {return typeof('+logical+');}}']+['internal static string @'+k+' {get {return GetResourceString('+json.dumps(k)+',null);}}' for k in values]+['}}'];(folder/'SR.Generated.cs').write_text('\n'.join(code)+'\n');E.SubElement(ig,'Compile',Include=native(folder/'SR.Generated.cs'));E.SubElement(ig,'EmbeddedResource',Include=native(resx),LogicalName=logical+'.resources');E.SubElement(ig,'EmbeddedResource',Include=native(original.parent/'Data/codepages.nlp'),LogicalName='codepages.nlp')
 target=E.SubElement(p,'Target',Name='CaptureInputs',BeforeTargets='CoreCompile')
 for name in ['Compile','ReferencePath','Analyzer']:E.SubElement(target,'WriteLinesToFile',File=native(folder/(name+'.txt')),Lines='@('+name+"->'%(FullPath)')",Overwrite='true')
 E.SubElement(target,'WriteLinesToFile',File=native(folder/'policy.txt'),Lines='$(TargetFramework)|$(TargetGroup)|$(TargetsWindows)|$(TargetsUnix)|$(DefineConstants)|$(NoWarn)|$(LangVersion)|$(TreatWarningsAsErrors)',Overwrite='true');E.indent(p);E.ElementTree(p).write(folder/'Library.csproj',encoding='utf-8',xml_declaration=True)
 run('build-'+profile,['/clang64/lib/dotnet/dotnet.exe','build',native(folder/'Library.csproj'),'-c','Release','--configfile',native(config),'-v:minimal'])
 dll=folder/'bin/Release'/(library+'.dll');results[profile]=dict(source_lineage=tag,source_commit=lineages[tag]['commit'],original_paths=spec['original_paths'],original_CSharp_inputs={str(f.relative_to(source)):sha(f) for f in selected},reference_sha256={native(f):sha(f) for f in refs},source_dependency_inputs=dependency,DLL_sha256=sha(dll),resources=values,codepages_nlp_sha256=sha(original.parent/'Data/codepages.nlp'))
 for name in spec['original_paths']:
  path=out/'assets'/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dll,path)
 print('PASS original CodePages4.5.1 implementation',profile,len(selected),'C# inputs',flush=True)
(out/'version.txt').write_bytes(('99ce22c306b07f99ddae60f443d23a983ae78f7b\r\n').encode());(out/'_._').write_bytes(b'')
(out/'results.json').write_text(json.dumps(dict(source_lineages=lineages,production_CSharp_changes=0,profiles=results,commands=commands,original_buildtools_host_replayed=False,full_dependency_goal_complete=False),indent=2)+'\n')
