"""Build a private source GenAPI bootstrap for metadata-to-C# contract ports."""
from pathlib import Path
import functools,hashlib,json,os,subprocess,sys,tarfile,xml.etree.ElementTree as E,shutil
archive,out=(Path(s).resolve() for s in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(archive)=='b4b4437762ce7ba35e19b8b564ac59a3097da1ebf6d11e464a50d5e2c74614f3'
source=out/'source';source.mkdir();hashes={}
with tarfile.open(archive) as t:
 assert t.pax_headers['comment']=='e9d13cbe7e8c1d52ce276a8655f52a87e1017c46'
 for m in t:
  n=m.name.partition('/')[2]
  if not m.isfile() or not (n.startswith(('src/GenAPI/Microsoft.DotNet.GenAPI/','src/Microsoft.DotNet.ApiSymbolExtensions/')) or n in {'LICENSE.txt','THIRD-PARTY-NOTICES.txt','Directory.Build.props','Directory.Build.targets','eng/Versions.props'}):continue
  if n.lower().endswith(('.dll','.exe','.pdb','.nupkg')):raise AssertionError(n)
  p=source/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(t.extractfile(m).read());hashes[n]=sha(p)
native=functools.lru_cache(None)(lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip())
config=out/'NuGet.config';config.write_text('<configuration><packageSources><clear/><add key="source" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources></configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1');commands=[];projects={};records={}
for name,rel in [('Microsoft.DotNet.ApiSymbolExtensions','src/Microsoft.DotNet.ApiSymbolExtensions'),('Microsoft.DotNet.GenAPI','src/GenAPI/Microsoft.DotNet.GenAPI'),('Generate','')]:
 folder=out/name;folder.mkdir();p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
 for k,v in dict(TargetFramework='net8.0',EnableDefaultItems='false',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',ImplicitUsings='enable',LangVersion='preview',Nullable='enable',TreatWarningsAsErrors='true',EnableNETAnalyzers='false',NuGetAudit='false',AssemblyName=name,RootNamespace=name,UseSharedCompilation='false').items():E.SubElement(pg,k).text=v
 ig=E.SubElement(p,'ItemGroup')
 for ns in ['System.Runtime.InteropServices','System.Text','System.Xml.Linq']:E.SubElement(ig,'Using',Include=ns)
 selected=[]
 if name=='Generate':
  E.SubElement(pg,'OutputType').text='Exe';E.SubElement(pg,'UseAppHost').text='false';shutil.copy2(here/'inputs/Generate.cs',folder/'Generate.cs');selected=[folder/'Generate.cs']
  for dep in ['Microsoft.DotNet.ApiSymbolExtensions','Microsoft.DotNet.GenAPI']:E.SubElement(ig,'ProjectReference',Include=native(projects[dep]))
 else:
  original=source/rel;selected=[f for f in sorted(original.rglob('*.cs')) if f.name!='MSBuildLog.cs'];assert selected
  E.SubElement(ig,'PackageReference',Include='Microsoft.CodeAnalysis.CSharp.Workspaces' if name.endswith('GenAPI') else 'Microsoft.CodeAnalysis.CSharp',Version='[4.8.0]')
  if name.endswith('GenAPI'):E.SubElement(ig,'ProjectReference',Include=native(projects['Microsoft.DotNet.ApiSymbolExtensions']))
  resource=original/'Resources.resx'
  if resource.exists():
   values={e.get('name'):e.findtext('value') for e in E.parse(resource).findall('data')};logical=name+'.Resources'
   code=['#nullable enable','namespace '+name+' { internal static class Resources { private static readonly System.Resources.ResourceManager manager=new System.Resources.ResourceManager('+json.dumps(logical)+',typeof(Resources).Assembly);internal static System.Globalization.CultureInfo? Culture {get;set;}']+['internal static string @'+k+' => manager.GetString('+json.dumps(k)+',Culture)!;' for k in values]+['}}'];(folder/'Resources.Generated.cs').write_text('\n'.join(code)+'\n');selected.append(folder/'Resources.Generated.cs');E.SubElement(ig,'EmbeddedResource',Include=native(resource),LogicalName=logical+'.resources')
 for f in selected:E.SubElement(ig,'Compile',Include=native(f))
 E.indent(p);project=folder/(name+'.csproj');E.ElementTree(p).write(project,encoding='utf-8',xml_declaration=True);projects[name]=project
 records[name]={'original_sources':{str(f.relative_to(source)):sha(f) for f in selected if f.is_relative_to(source)},'generated_inputs':[native(f) for f in selected if not f.is_relative_to(source)]}
cmd=['/clang64/lib/dotnet/dotnet.exe','build',native(projects['Generate']),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal']
with (out/'build.log').open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(out/'build.log').read_text(errors='replace')[-14000:]
(out/'results.json').write_text(json.dumps(dict(source_archive_sha256=sha(archive),source_commit='e9d13cbe7e8c1d52ce276a8655f52a87e1017c46',original_file_sha256=hashes,projects=records,production_source_changes=0,source_bootstrap_workspace_packages='4.8.0',original_SDK_declared_workspaces_version='4.8.0-3.23524.11',private_bootstrap_tool_not_original_SDK_GenAPI_distribution=True,source_NET8_profile_originally_supported_by_DotNetBuildFromSource=True,commands=commands,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS private source GenAPI metadata bootstrap')
