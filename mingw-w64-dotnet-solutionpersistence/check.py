"""Restore exact source archives and exercise APIs and real solution serialization."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as E,zipfile
prepared,check=(Path(p).resolve() for p in sys.argv[1:3]);feed=Path(sys.argv[3]).resolve() if len(sys.argv)==4 else prepared/'feed'
assert not check.exists();check.mkdir(parents=True);here=Path(__file__).resolve().parent
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record=json.loads((prepared/'source-inputs.json').read_text());source=Path(record['source_root'].replace('E:/','/e/'));main=source/'src/Microsoft.VisualStudio.SolutionPersistence'
baseline=check/'api.txt';baseline.write_text('\n'.join((main/'PublicAPI'/n).read_text().rstrip() for n in ['PublicAPI.Shipped.txt','PublicAPI.Unshipped.txt'])+'\n')
tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',OutputType='Exe',UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='enable',LangVersion='preview',UseSharedCompilation='false',CscToolPath=native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap')),CscToolExe='csc53.cmd',WarningsAsErrors='NU1608').items():E.SubElement(pg,k).text=v
items=E.SubElement(tree,'ItemGroup')
for n in ['Check.cs','CheckApi.cs']:E.SubElement(items,'Compile',Include=native(here/'inputs'/n))
for n,v in [('Microsoft.VisualStudio.SolutionPersistence','1.0.52'),('Microsoft.CodeAnalysis.CSharp','5.3.0-2.26113.113')]:E.SubElement(items,'PackageReference',Include=n,Version='['+v+']')
E.ElementTree(tree).write(check/'Check.csproj',encoding='utf-8',xml_declaration=True)
config=E.Element('configuration');sources=E.SubElement(config,'packageSources');E.SubElement(sources,'clear')
for i,path in enumerate([feed,Path('/clang64/lib/dotnet/library-packs')]):E.SubElement(sources,'add',key='source'+str(i),value=native(path))
E.ElementTree(config).write(check/'NuGet.config',encoding='utf-8',xml_declaration=True)
host='/clang64/lib/dotnet/dotnet.exe';env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(check/'cli-home'),NUGET_PACKAGES=native(check/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1');commands=[]
def run(label,command):
 with (check/(label+'.log')).open('w') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(label=label,command=command,exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
run('build',[host,'build',native(check/'Check.csproj'),'-c','Release','--configfile',native(check/'NuGet.config'),'-v:minimal'])
binary=check/'bin/Release/net8.0';package=feed/'microsoft.visualstudio.solutionpersistence.1.0.52.nupkg'
if not package.exists():package=feed/'Microsoft.VisualStudio.SolutionPersistence.1.0.52.nupkg'
assert package.read_bytes()==(prepared/'feed/Microsoft.VisualStudio.SolutionPersistence.1.0.52.nupkg').read_bytes()
assert package.read_bytes()==(check/'cache/microsoft.visualstudio.solutionpersistence/1.0.52/microsoft.visualstudio.solutionpersistence.1.0.52.nupkg').read_bytes()
with zipfile.ZipFile(package) as z:assert z.read('lib/net8.0/Microsoft.VisualStudio.SolutionPersistence.dll')==(binary/'Microsoft.VisualStudio.SolutionPersistence.dll').read_bytes()
outputs=check/'outputs λ';outputs.mkdir()
run('run',[host,native(binary/'Check.dll'),native(Path('/clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0')),native(baseline),native(outputs),native(source/'test/Microsoft.VisualStudio.SolutionPersistence.Tests/SlnAssets')])
(check/'results.json').write_text(json.dumps(dict(commands=commands,source_package_sha256=sha(package),exact_package_cache_and_loaded_dll_bytes_match=True,original_net8_api_and_serializer_consumer_passed=True,upstream_roundtrip_vectors=5,unicode_sln_and_slnx_roundtrips_passed=True,invalid_xml_rejected=True,sln_read_cancellation_passed=True,upstream_xml_read_ignores_precanceled_token=True,formal_installed_feed=len(sys.argv)==4,other_net472_profile_built=False,full_msbuild_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS exact source SolutionPersistence NET8 API/serializer consumer and five original vectors')
