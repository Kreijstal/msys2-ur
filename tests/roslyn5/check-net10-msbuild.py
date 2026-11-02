"""Verify SDK8's original MSBuild Csc task launches the installed NET10 compiler."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as E
prefix,out=(Path(p).resolve() for p in sys.argv[1:3]);assert not out.exists();out.mkdir(parents=True)
tool=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap';assert (tool/'csc53.cmd').is_file()
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
project=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(project,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',OutputType='Exe',UseAppHost='false',EnableNETAnalyzers='false',NuGetAudit='false',LangVersion='14',UseSharedCompilation='false',CscToolPath=native(tool),CscToolExe='csc53.cmd').items():E.SubElement(props,k).text=v
path=out/'CompilerTask.csproj';E.ElementTree(project).write(path,encoding='utf-8',xml_declaration=True)
(out/'Program λ.cs').write_text('''using System;
public static class ExtensionProbe { extension(string text) { public int TwiceLength => text.Length * 2; } }
class Program { static int Main() { if ("source".TwiceLength != 12) return 1; Console.WriteLine("PASS SDK8 MSBuild Csc task -> original NET10 Roslyn5.3 -> CSharp14 NET8 application"); return 0; } }
''',encoding='utf-8')
feed=prefix/'lib/dotnet/library-packs'
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="installed-source" value="'+native(feed)+'"/></packageSources></configuration>\n')
dotnet=prefix/'lib/dotnet/dotnet.exe'
env=dict(os.environ,DOTNET_ROOT=native(dotnet.parent),DOTNET_ROOT_X64=native(dotnet.parent),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1')
commands=[]
def run(label,command):
 with (out/(label+'.log')).open('w') as f:r=subprocess.run(command,env=env,stdout=f,stderr=subprocess.STDOUT)
 commands.append(dict(label=label,command=command,exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
run('msbuild',[str(dotnet),'build',native(path),'-c','Release','--configfile',native(out/'NuGet.config'),'-p:UseSharedCompilation=false','-v:diag'])
log=(out/'msbuild.log').read_text();assert 'csc53.cmd' in log and '/langversion:14' in log
run('execute',[str(dotnet),native(out/'bin/Release/net8.0/CompilerTask.dll')])
assert 'PASS SDK8 MSBuild Csc task' in (out/'execute.log').read_text()
(out/'results.json').write_text(json.dumps(dict(commands=commands,installed_compiler_sha256=hashlib.sha256((tool/'csc.dll').read_bytes()).hexdigest(),original_sdk8_csc_task_launches_net10_compiler=True,original_sdk10_tasks_built=False,compiler_server_verified=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original SDK8 Csc task launches installed source NET10 csc53.cmd and executes CSharp14 output')
