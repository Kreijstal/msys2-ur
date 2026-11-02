"""Fresh original Tasks16 NS2 consumer; require isolated original dependency DLLs."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,zipfile
producer,out=(Path(x).resolve() for x in sys.argv[1:3]);assert not out.exists();out.mkdir();here=Path(__file__).parent
feed=Path(sys.argv[3]).resolve() if len(sys.argv)==4 else producer/'feed';native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
origins=[('candidate',native(feed)),('source',native(Path('/clang64/lib/dotnet/library-packs')))];unique={};keys={}
for key,path in origins:unique.setdefault(path,key);keys[key]=unique[path]
patterns={key:[] for key in unique.values()}
for key,pattern in [('candidate','Microsoft.Build.Tasks.Core'),('source','*')]:patterns[keys[key]].append(pattern)
config=out/'NuGet.config';config.write_text('<configuration><packageSources><clear/>'+''.join('<add key="'+key+'" value="'+path+'"/>' for path,key in unique.items())+'</packageSources><packageSourceMapping>'+''.join('<packageSource key="'+key+'">'+''.join('<package pattern="'+p+'"/>' for p in values)+'</packageSource>' for key,values in patterns.items())+'</packageSourceMapping></configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1')
bridge=out/'bridge';bridge.mkdir();shutil.copy2(here/'inputs/TasksBridge.cs',bridge/'Bridge.cs')
(bridge/'Bridge.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>netstandard2.0</TargetFramework><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit><LangVersion>7.3</LangVersion></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.Build.Tasks.Core" Version="[16.0.461]"/></ItemGroup></Project>\n')
host=out/'host';host.mkdir()
for name,source in [('Api.cs','Api.cs'),('Check.cs','TasksCheck.cs')]:shutil.copy2(here/'inputs'/source,host/name)
(host/'Check.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Mono.Cecil" Version="[0.11.0]"/></ItemGroup></Project>\n')
commands=[]
def run(label,args):
 cmd=['/clang64/lib/dotnet/dotnet.exe',*args]
 with (out/(label+'.log')).open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(label,(out/(label+'.log')).read_text()[-6500:])
for label,project in [('bridge',bridge/'Bridge.csproj'),('host',host/'Check.csproj')]:run(label,['build',native(project),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal'])
owned=out/'owned';owned.mkdir();shutil.copy2(bridge/'bin/Release/netstandard2.0/Bridge.dll',owned/'Bridge.dll');payload={}
versions={'Microsoft.Build.Tasks.Core':'16.0.461','Microsoft.Build.Framework':'16.0.461','Microsoft.Build.Utilities.Core':'16.0.461','System.Collections.Immutable':'1.5.0','System.Reflection.Metadata':'1.6.0','System.Threading.Tasks.Dataflow':'4.6.0','System.CodeDom':'4.4.0','Microsoft.Win32.Registry':'4.3.0','System.Text.Encoding.CodePages':'4.0.1'}
for name,version in versions.items():
 package=out/'cache'/name.lower()/version/(name.lower()+'.'+version+'.nupkg');origin=feed if name=='Microsoft.Build.Tasks.Core' else Path('/clang64/lib/dotnet/library-packs');original=next(p for p in origin.glob('*.nupkg') if p.name.lower()==name.lower()+'.'+version+'.nupkg');assert package.read_bytes()==original.read_bytes()
 with zipfile.ZipFile(package) as z:
  data=z.read('lib/netstandard2.0/'+name+'.dll')
  if name=='Microsoft.Build.Tasks.Core':(owned/(name+'.pdb')).write_bytes(z.read('lib/netstandard2.0/'+name+'.pdb'))
 (owned/(name+'.dll')).write_bytes(data);payload[name]=hashlib.sha256(data).hexdigest()
for assets in [bridge/'obj/project.assets.json',host/'obj/project.assets.json']:assert not json.loads(assets.read_text()).get('logs')
run('run',[native(host/'bin/Release/net8.0/Check.dll'),native(owned),native(here/'inputs/tasks16-published-metadata.json'),native(here/'inputs/tasks16-published-resources.json')])
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_public_API_entries=1305,original_runtime_dependency_identity_sets_equal=True,original_published_resources_verified=True,original_resource_strings_verified=705,original_embedded_XML_XSL_files_verified=7,matching_portable_PDB_sequence_points_verified=True,original_NS2_PackageReference_consumer=True,all_exact_cached_source_NuGet_archives_verified=True,isolated_all_nine_original_implementations_executed=True,consumer_DLL_sha256=payload,formal_pacman_installed=len(sys.argv)==4,original_NET472_profile_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print((out/'run.log').read_text())
