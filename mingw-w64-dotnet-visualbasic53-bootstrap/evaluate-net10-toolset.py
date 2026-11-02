"""Evaluate all original VMR compiler CLI projects with the source SDK8 host."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as E

prepared,tool,plan=(Path(p).resolve() for p in sys.argv[1:4])
assert not tool.exists();tool.mkdir();assert not plan.exists()
here=Path(__file__).resolve().parent
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
project=E.parse(prepared/'evaluation-tool/Build.csproj')
for item in project.iter('Compile'):item.set('Include',native(here/'EvaluateNet10Projects.cs'))
project.find('.//AssemblyName').text='EvaluateNet10Projects'
E.ElementTree(project.getroot()).write(tool/'Build.csproj',encoding='utf-8',xml_declaration=True)
dotnet='/clang64/lib/dotnet/dotnet.exe';sdk=Path('/clang64/lib/dotnet/sdk/8.0.131')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_HOME=native(tool/'cli-home'),NUGET_PACKAGES=native(tool/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1')
commands=[]
def run(command,log):
 with log.open('w') as output:result=subprocess.run(command,env=env,stdout=output,stderr=subprocess.STDOUT)
 commands.append(dict(command=command,exit_code=result.returncode));assert result.returncode==0,log
run([dotnet,'build',native(tool/'Build.csproj'),'-c','Release','--configfile',native(prepared/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],tool/'build.log')
run(['/usr/bin/python3',str(here/'prepare-net10-projects.py'),str(prepared/'roslyn-source'),str(plan),'--toolset'],tool/'prepare.log')
env.update(MSBuildSDKsPath=native(sdk/'Sdks'),MSBUILD_EXE_PATH=native(sdk/'MSBuild.dll'))
run([dotnet,native(tool/'bin/Release/net8.0/EvaluateNet10Projects.dll'),native(plan/'wrappers.json'),native(plan/'evaluated.json')],tool/'evaluate.log')
model=json.loads((plan/'evaluated.json').read_text());assert len(model)==6
for name,entry in model.items():
 assert entry['properties']['TargetFramework']=='net10.0',name
 assert 'net10.0' in entry['properties']['TargetFrameworks'].split(';'),name
 assert all('RazorCompiler' not in i['identity'] for i in entry['items']['ProjectReference']),name
 assert not any(i['identity']=='Microsoft.DiaSymReader.Native' for i in entry['items']['PackageReference']),name
counts={n:len(r['items']['Compile']) for n,r in model.items()};assert counts['vbc']==11 and counts['VBCSCompiler']==27,counts
(tool/'results.json').write_text(json.dumps(dict(commands=commands,original_compile_items=counts,source_only_net10_profile_evaluated=True,net472_razor_and_native_symbol_reader_excluded_by_original_conditions=True,compiled=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS six original NET10 compiler projects:',counts)
