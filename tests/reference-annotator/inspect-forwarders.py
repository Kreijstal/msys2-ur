"""Read all original Vectors4.4 exported type records without loading its DLLs."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,zipfile
package,out=map(lambda s:Path(s).resolve(),sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).parent
assert hashlib.sha256(package.read_bytes()).hexdigest()=='6ae5d02b67e52ff2699c1feb11c01c526e2f60c09830432258e0809486aabb65'
files=[]
with zipfile.ZipFile(package) as z:
 for name in z.namelist():
  if name.endswith('.dll'):
   assert name.startswith(('lib/','ref/')) and '..' not in Path(name).parts
   p=out/'metadata-only'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name));files.append(p)
assert len(files)==7
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
host=out/'host';host.mkdir();shutil.copy2(here/'InspectForwarders.cs',host/'Program.cs')
(host/'Inspect.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Mono.Cecil" Version="[0.11.0]"/></ItemGroup></Project>\n')
config=out/'NuGet.config';config.write_text('<configuration><packageSources><clear/><add key="source" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources></configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1');dotnet='/clang64/lib/dotnet/dotnet.exe';commands=[]
for label,cmd in [('build',[dotnet,'build',native(host/'Inspect.csproj'),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal']),('metadata',[dotnet,native(host/'bin/Release/net8.0/Inspect.dll'),native(out/'forwarders-native.json')]+[native(p) for p in files])]:
 with (out/(label+'.log')).open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(label,(out/(label+'.log')).read_text(errors='replace'))
raw=json.loads((out/'forwarders-native.json').read_text());profiles={}
for p in files:
 key=p.relative_to(out/'metadata-only').as_posix();profiles[key]=dict(raw[native(p)],DLL_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
report=dict(original_package_sha256=hashlib.sha256(package.read_bytes()).hexdigest(),published_DLL_executed_or_used_as_compiler_reference=False,commands=commands,profiles=profiles)
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({p:v['exported_types'] for p,v in profiles.items()},indent=2))
