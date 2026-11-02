"""Build both original Dataflow4.6 Standard1.0/1.1 projects with exact old contracts."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tarfile,xml.etree.ElementTree as E

archive,contracts,out,compiler=(Path(s).resolve() for s in sys.argv[1:]);assert not out.exists();out.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive)=='986a512c70d55ed7a1ed8cbb9d8323017c9cc83e77e95e833c7b91f42e4ef601'
commit='9688ddbb62c04189cac4c4a06e31e93377dccd41';here=Path(__file__).parent
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
source=out/'source';source.mkdir();hashes={}
with tarfile.open(archive) as t:
 assert t.pax_headers['comment']==commit
 for m in t:
  if not m.isfile():continue
  rel=m.name.partition('/')[2]
  if not (rel.startswith(('src/System.Threading.Tasks.Dataflow/','src/Common/src/')) or rel in {'dir.props','dir.targets','LICENSE','THIRD-PARTY-NOTICES'}):continue
  data=t.extractfile(m).read();assert data[:2]!=b'MZ' and not rel.lower().endswith(('.dll','.exe','.pdb','.nupkg')),rel
  p=source/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);hashes[rel]=hashlib.sha256(data).hexdigest()
key=here/'inputs/Microsoft.snk';assert hashlib.sha1(key.read_bytes()).digest()[-8:][::-1].hex()=='b03f5f7f11d50a3a'
matrix=json.loads((here/'inputs/source-contract-build-matrix.json').read_text())
config=out/'NuGet.config';config.write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1')
profiles={};commands=[]
for tfm,filename,dependency_json in [('netstandard1.0','System.Threading.Tasks.Dataflow.WP8.csproj','wp8/project.json'),('netstandard1.1','System.Threading.Tasks.Dataflow.csproj','project.json')]:
 folder=out/tfm;folder.mkdir();component=source/'src/System.Threading.Tasks.Dataflow/src';original=component/filename
 shutil.copytree(component/'XmlDocs',folder/'XmlDocs')
 tree=E.parse(original).getroot()
 for node in tree.iter():node.tag=node.tag.rsplit('}',1)[-1]
 for node in list(tree):
  if node.tag=='Import':tree.remove(node)
 for node in tree.iter():
  if node.tag in {'Compile','None','Content','EmbeddedResource'} and node.get('Include'):
   node.set('Include',native(original.parent/node.get('Include').replace('\\','/')))
 E.indent(tree);E.ElementTree(tree).write(folder/'upstream.proj',encoding='utf-8',xml_declaration=True)
 roots=json.loads((component/dependency_json).read_text())['frameworks'][tfm]['dependencies'];selected=set()
 def select(k):
  if k in selected:return
  selected.add(k)
  for dep in matrix[k]['references']:
   name,version=dep.split(', Version=');select(name+'/'+version.split(',')[0])
 for name in roots:
  if name!='Microsoft.NETCore.Platforms':select(name+'/4.0.0.0')
 refs=[contracts/k/(k.split('/')[0]+'.dll') for k in sorted(selected)];assert all(p.is_file() for p in refs)
 p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
 props=dict(TargetFramework=tfm,DisableImplicitFrameworkReferences='true',NoStdLib='true',AddAdditionalExplicitAssemblyReferences='false',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultItems='false',CommonPath=native(source/'src/Common/src'),ConfigurationGroup='Release',TargetGroup='',GenerateAssemblyInfo='false',GenerateTargetFrameworkAttribute='false',TreatWarningsAsErrors='true',LangVersion='6',Nullable='disable',EnableNETAnalyzers='false',CheckEolTargetFramework='false',NuGetAudit='false',UseSharedCompilation='false',AllowUnsafeBlocks='true',SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile=native(key),IsPackable='false')
 for k,v in props.items():E.SubElement(pg,k).text=v
 E.SubElement(p,'Import',Project='upstream.proj');ig=E.SubElement(p,'ItemGroup')
 for ref in refs:
  item=E.SubElement(ig,'Reference',Include=ref.stem);E.SubElement(item,'HintPath').text=native(ref);E.SubElement(item,'Private').text='false'
 for name in [native(source/'src/Common/src/System/SR.cs'),'SR.Generated.cs','BootstrapVersion.cs']:E.SubElement(ig,'Compile',Include=name)
 logical='FxResources.System.Threading.Tasks.Dataflow.SR';resource=component/'Resources/Strings.resx'
 E.SubElement(ig,'EmbeddedResource',Include=native(resource),LogicalName=logical+'.resources')
 strings={e.get('name'):e.findtext('value') for e in E.parse(resource).findall('data')}
 code=['namespace FxResources.System.Threading.Tasks.Dataflow { internal static class SR {} }','namespace System { internal partial class SR { private static System.Type ResourceType { get { return typeof('+logical+'); } }']
 for ident in strings:
  assert ident.isidentifier();code.append('internal static string @'+ident+' { get { return GetResourceString('+json.dumps(ident)+', null); } }')
 code.append('}}');(folder/'SR.Generated.cs').write_text('\n'.join(code)+'\n')
 (folder/'BootstrapVersion.cs').write_text('[assembly:System.Reflection.AssemblyFileVersion("1.0.24212.01")]\n[assembly:System.Reflection.AssemblyInformationalVersion("Source-built CoreFX '+commit+'; original '+tfm+'; source SDK8/Csc4.4 bootstrap")]\n[assembly:System.CLSCompliant(true)]\n[assembly:System.Resources.NeutralResourcesLanguage("en-US")]\n')
 # The original project AssemblyVersion property is preserved above, but the
 # bootstrap disables SDK-generated metadata, so emit its original value here.
 with (folder/'BootstrapVersion.cs').open('a') as f:f.write('[assembly:System.Reflection.AssemblyVersion("4.6.0.0")]\n')
 target=E.SubElement(p,'Target',Name='CaptureOriginalInputs',BeforeTargets='CoreCompile')
 for kind in ['Compile','ReferencePath','Analyzer']:E.SubElement(target,'WriteLinesToFile',File='$(IntermediateOutputPath)'+kind+'.txt',Lines='@('+kind+"->'%(FullPath)')",Overwrite='true')
 E.SubElement(target,'WriteLinesToFile',File='$(IntermediateOutputPath)policy.txt',Lines='$(TargetFramework)|$(DefineConstants)|$(NoWarn)|$(LangVersion)|$(TreatWarningsAsErrors)',Overwrite='true')
 E.indent(p);E.ElementTree(p).write(folder/'Library.csproj',encoding='utf-8',xml_declaration=True)
 cmd=['/clang64/lib/dotnet/dotnet.exe','build',native(folder/'Library.csproj'),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-p:CscToolPath='+native(compiler),'-p:CscToolExe=csc44.cmd','-v:minimal']
 with (folder/'build.log').open('w') as log:result=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(command=cmd,exit_code=result.returncode));assert result.returncode==0,(tfm,(folder/'build.log').read_text()[-7000:])
 profiles[tfm]=dict(original_project=filename,original_dependency_json=dependency_json,reference_sha256={k:sha(contracts/k/(k.split('/')[0]+'.dll')) for k in sorted(selected)},resources=strings,production_CSharp_changes=0)
 (out/'results.json').write_text(json.dumps(dict(source_commit=commit,source_archive_sha256=sha(archive),original_file_sha256=hashes,profiles=profiles,commands=commands,source_SDK8_NET8_host=True,original_buildtools_host_replayed=False,formal_package_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
 print('PASS original Dataflow4.6',tfm,'source build with',len(refs),'exact lower contracts',flush=True)
