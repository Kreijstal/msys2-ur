"""Build the complete original two-source Arcade templating task for the NET8 host."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tarfile,xml.etree.ElementTree as E
root=Path(sys.argv[1]).resolve();plan=Path(sys.argv[2]).resolve();out=plan/'tools/Templating';out.mkdir()
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
archive=root/'arcade-runtime10-4bf37ce6.tar.gz';assert sha(archive)=='82f5f6dd63c0dcf3c0fc49b282207db5d889d9cc0939589d43b16c7fcfdf7d66'
inputs={}
with tarfile.open(archive) as tar:
 for m in tar:
  relative=m.name.partition('/')[2]
  if m.isfile() and relative.startswith('src/Microsoft.DotNet.Build.Tasks.Templating/src/') and relative.endswith(('.cs','.csproj','.props')):
   p=out/Path(relative).name;p.write_bytes(tar.extractfile(m).read());inputs[relative]=sha(p)
cs=sorted(out.glob('*.cs'));assert len(cs)==2
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',AssemblyName='Microsoft.DotNet.Build.Tasks.Templating',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='disable',LangVersion='preview',CscToolPath=native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')),CscToolExe='csc50.cmd').items():E.SubElement(pg,k).text=v
ig=E.SubElement(p,'ItemGroup')
for file in cs:E.SubElement(ig,'Compile',Include=native(file))
for name in ['Microsoft.Build.Framework','Microsoft.Build.Utilities.Core']:
 r=E.SubElement(ig,'Reference',Include=name);E.SubElement(r,'HintPath').text=native(Path('/clang64/lib/dotnet/sdk/8.0.131')/(name+'.dll'));E.SubElement(r,'Private').text='false'
E.indent(p);E.ElementTree(p).write(out/'Build.csproj',encoding='utf-8',xml_declaration=True)
command=['/clang64/lib/dotnet/dotnet.exe','build',native(out/'Build.csproj'),'-c','Release','--configfile',native(plan/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal']
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(plan/'cli-home'),NUGET_PACKAGES=native(plan/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
with (out/'build.log').open('w') as f:r=subprocess.run(command,env=env,stdout=f,stderr=subprocess.STDOUT)
assert r.returncode==0,(r.returncode,out/'build.log')
(out/'source-inputs.json').write_text(json.dumps(dict(original_arcade_inputs=inputs,original_production_cs=2,production_cs_changes=0,bootstrap_framework='net8.0',original_frameworks=['net10.0','net472'],original_tool_profiles_complete=False),indent=2)+'\n')
print('PASS complete original Arcade templating task built on NET8 host')
