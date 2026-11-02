"""Build all original Tasks.Extensions4.5.3 runtime/reference profiles from unchanged source."""
from pathlib import Path
import functools,hashlib,json,os,subprocess,sys,tarfile,xml.etree.ElementTree as E
archive,out,compiler=(Path(s).resolve() for s in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();commit='637a8d58f72f2b0f1a71187530c3cf433e95a75a'
assert sha(archive)=='a4ac86f506488ca48f5b33c4fd0321bcd7b2de17afe0c516bb3879997bc67bbf'
source=out/'source';source.mkdir();hashes={}
with tarfile.open(archive) as t:
 assert t.pax_headers['comment']==commit
 for m in t:
  n=m.name.partition('/')[2]
  if not m.isfile() or not (n.startswith(('src/System.Threading.Tasks.Extensions/','src/Common/src/')) or n in {'src/Common/src/System/SR.cs','src/Common/tests/System/Threading/Tasks/Sources/ManualResetValueTaskSource.cs','LICENSE.TXT','THIRD-PARTY-NOTICES.TXT','dir.props','dir.targets','src/dir.props','src/dir.targets','Packaging.props','external/docs/docs.depproj','pkg/useSharedDesignerContext.txt'}):continue
  assert '..' not in Path(n).parts and not n.lower().endswith(('.dll','.exe','.pdb','.nupkg'))
  data=t.extractfile(m).read();assert data[:2]!=b'MZ';p=source/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);hashes[n]=sha(p)
native=functools.lru_cache(None)(lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip())
key=bytes.fromhex((here/'inputs/Open.pubkey.hex').read_text());assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='cc7b13ffcd2ddd51';(out/'Open.pubkey').write_bytes(key)
contracts=Path('/clang64/lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts');matrix=json.loads((here/'inputs/source-contract-build-matrix.json').read_text())
version=json.loads((here/'inputs/native-version-policy.json').read_text(encoding='utf-8-sig'));commands=[];profiles={}
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1')
config=out/'NuGet.config';config.write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
def run(label,cmd,cwd=None):
 with (out/(label+'.log')).open('w') as log:r=subprocess.run(cmd,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(label,(out/(label+'.log')).read_text(errors='replace')[-7000:])
for kind in ['lib']:

 original=source/'src/System.Threading.Tasks.Extensions'/('src' if kind=='lib' else 'ref')/'System.Threading.Tasks.Extensions.csproj';project=E.parse(original)
 selected=[(original.parent/e.get('Include').replace('$(CommonPath)','../../Common/src').replace('\\','/')).resolve() for e in project.findall('.//{*}Compile')]
 for tfm in ['netstandard1.0','netstandard2.0']:
  folder=out/kind/tfm;folder.mkdir(parents=True);baseline=json.loads((here/'inputs'/('published-'+kind+'-'+tfm+'.json')).read_text())['System.Threading.Tasks.Extensions.dll']
  dep=Path('/clang64/lib/dotnet/library-packs/system.runtime.compilerservices.unsafe.4.5.2.nupkg');depfile=folder/'source-dependencies/System.Runtime.CompilerServices.Unsafe.dll';depfile.parent.mkdir()
  import zipfile
  depasset='ref/'+tfm+'/System.Runtime.CompilerServices.Unsafe.dll'
  with zipfile.ZipFile(dep) as z:depfile.write_bytes(z.read(depasset))
  closure=set()
  def select(k):
   if k in closure:return
   assert k in matrix,k;closure.add(k)
   for r in matrix[k]['references']:
    name,v=r.split(', Version=');select(name+'/'+v.split(',')[0])
  if tfm=='netstandard1.0':
   for entry in project.findall('.//{*}Reference'):
    name=entry.get('Include')
    if name!='System.Runtime.CompilerServices.Unsafe':select(name+'/4.0.0.0')
   refs=[contracts/k/(k.split('/')[0]+'.dll') for k in sorted(closure)]
  else:refs=sorted(Path('/clang64/lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll'))
  refs.append(depfile)
  assert refs and all(p.is_file() for p in refs)
  info=['[assembly:System.Reflection.AssemblyVersion("4.2.0.1")]']
  for attr in baseline['attributes']:
   name=attr['type']
   if name.startswith('System.Reflection.') or name in {'System.CLSCompliantAttribute','System.Resources.NeutralResourcesLanguageAttribute','System.Security.AllowPartiallyTrustedCallersAttribute','System.Runtime.CompilerServices.ReferenceAssemblyAttribute'}:
    values=[v.lower() if name=='System.CLSCompliantAttribute' else json.dumps(v) for v in attr['arguments']];info.append('[assembly:'+name+'('+','.join(values)+')]')
  (folder/'Version.cs').write_text('\n'.join(info)+'\n')
  v=version[kind+'/'+tfm];rc=['LANGUAGE 0,0','1 VERSIONINFO','FILEVERSION '+','.join(str(v['File'+n+'Part']) for n in ['Major','Minor','Build','Private']),'PRODUCTVERSION '+','.join(str(v['Product'+n+'Part']) for n in ['Major','Minor','Build','Private']),'FILEFLAGSMASK 0x3f','FILEFLAGS 0','FILEOS 4','FILETYPE 2','FILESUBTYPE 0','BEGIN','BLOCK "StringFileInfo"','BEGIN','BLOCK "000004b0"','BEGIN']
  for k in ['CompanyName','FileDescription','FileVersion','InternalName','LegalCopyright','OriginalFilename','ProductVersion','ProductName','Comments','LegalTrademarks','PrivateBuild','SpecialBuild']:rc.append('VALUE '+json.dumps(k)+', L'+json.dumps(v[k],ensure_ascii=True).replace('\\u','\\x'))
  rc+=['END','END','BLOCK "VarFileInfo"','BEGIN','VALUE "Translation", 0, 1200','END','END'];(folder/'version.rc').write_text('\n'.join(rc)+'\n')
  run('rc-'+kind+'-'+tfm,['/clang64/bin/llvm-rc.exe','-fo','version.res','version.rc'],folder)
  p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
  props=dict(TargetFramework=tfm,DisableImplicitFrameworkReferences='true',NoStdLib='true',NoConfig='true',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',GenerateAssemblyInfo='false',GenerateTargetFrameworkAttribute='false',AssemblyName='System.Threading.Tasks.Extensions',TargetGroup='netstandard' if tfm=='netstandard2.0' else tfm,IsPartialFacadeAssembly='false',AllowUnsafeBlocks='true',LangVersion='7.3',WarningLevel='4',NoWarn='1701;1702',TreatWarningsAsErrors='true',Nullable='disable',SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile=native(out/'Open.pubkey'),Win32Resource=native(folder/'version.res'),CscToolPath=native(compiler),CscToolExe='csc44.cmd',UseSharedCompilation='false',DebugType='portable',Optimize='true',DefineConstants='TRACE;netstandard',AppendTargetFrameworkToOutputPath='false',AppendRuntimeIdentifierToOutputPath='false',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false')
  if kind=='lib':props['DocumentationFile']=native(folder/'bin/Release/System.Threading.Tasks.Extensions.xml')
  for k,v in props.items():E.SubElement(pg,k).text=v
  ig=E.SubElement(p,'ItemGroup')
  for f in selected+[folder/'Version.cs']:E.SubElement(ig,'Compile',Include=native(f))
  for f in refs:E.SubElement(ig,'Reference',Include=f.stem,HintPath=native(f),Private='false')
  values={}
  target=E.SubElement(p,'Target',Name='CaptureInputs',BeforeTargets='CoreCompile')
  for name in ['Compile','ReferencePath','Analyzer']:E.SubElement(target,'WriteLinesToFile',File=native(folder/(name+'.txt')),Lines='@('+name+"->'%(FullPath)')",Overwrite='true')
  E.SubElement(target,'WriteLinesToFile',File=native(folder/'policy.txt'),Lines='$(TargetFramework)|$(TargetGroup)|$(DefineConstants)|$(NoWarn)|$(LangVersion)|$(TreatWarningsAsErrors)',Overwrite='true')
  E.indent(p);E.ElementTree(p).write(folder/'Library.csproj',encoding='utf-8',xml_declaration=True)
  run('build-'+kind+'-'+tfm,['/clang64/lib/dotnet/dotnet.exe','build',native(folder/'Library.csproj'),'-c','Release','--configfile',native(config),'-v:minimal'])
  profiles[kind+'/'+tfm]=dict(original_CSharp_inputs={str(f.relative_to(source)):sha(f) for f in selected},reference_sha256={native(f):sha(f) for f in refs},DLL_sha256=sha(folder/'bin/Release/System.Threading.Tasks.Extensions.dll'),resources=values,source_dependency_inputs=dict(package=dep.name,package_sha256=sha(dep),asset=depasset,DLL_sha256=sha(depfile)))
  print('PASS original Tasks.Extensions4.5.3 profile',kind,tfm,flush=True)
documentation=json.loads((here/'inputs/published-provenance.json').read_text())
assert (here/'inputs/ManualResetValueTaskSource.cs').read_bytes()==(source/'src/Common/tests/System/Threading/Tasks/Sources/ManualResetValueTaskSource.cs').read_bytes()
import shutil
alias=out/'lib/portable-net45+win8+wp8+wpa81/bin/Release';alias.mkdir(parents=True)
shutil.copy2(out/'lib/netstandard1.0/bin/Release/System.Threading.Tasks.Extensions.dll',alias/'System.Threading.Tasks.Extensions.dll')
(out/'version.txt').write_bytes((commit+'\r\n').encode())
(out/'_._').write_bytes(b'')
(out/'results.json').write_text(json.dumps(dict(source_commit=commit,source_archive_sha256=sha(archive),original_file_sha256=hashes,production_CSharp_changes=0,profiles=profiles,commands=commands,documentation= documentation,original_buildtools_host_replayed=False,source_Csc44_NET8_bootstrap=True,full_dependency_goal_complete=False),indent=2)+'\n')
