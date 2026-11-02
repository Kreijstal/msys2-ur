"""Use SDK8's original Vbc task to invoke installed source NET10 vbc53.cmd."""
from pathlib import Path
import json,os,subprocess,sys,xml.etree.ElementTree as E
prefix,out=(Path(p).resolve() for p in sys.argv[1:3]);assert not out.exists();out.mkdir(parents=True)
tool=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap';assert (tool/'vbc53.cmd').is_file()
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',OutputType='Exe',UseAppHost='false',EnableNETAnalyzers='false',NuGetAudit='false',UseSharedCompilation='false',RootNamespace='',OptionStrict='On',OptionInfer='On',VbcToolPath=native(tool),VbcToolExe='vbc53.cmd').items():E.SubElement(props,k).text=v
E.ElementTree(p).write(out/'CompilerTask.vbproj',encoding='utf-8',xml_declaration=True)
(out/'Program λ.vb').write_text('Imports System\nImports System.Linq\nModule Program\n Sub Main()\n Dim q=From n In {1,2,3} Select n*2\n If q.Sum()<>12 Then Throw New Exception("Query result")\n Console.WriteLine("PASS SDK8 Vbc task launches source NET10 VB5.3 and executes emitted NET8 query program")\n End Sub\nEnd Module\n',encoding='utf-8')
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="source" value="'+native(prefix/'lib/dotnet/library-packs')+'"/></packageSources></configuration>\n')
host=prefix/'lib/dotnet/dotnet.exe';env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1');commands=[]
for label,command in [('msbuild',[str(host),'build',native(out/'CompilerTask.vbproj'),'-c','Release','--configfile',native(out/'NuGet.config'),'-p:UseSharedCompilation=false','-v:diag']),('execute',[str(host),native(out/'bin/Release/net8.0/CompilerTask.dll')])]:
 with (out/(label+'.log')).open('w') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(label=label,command=command,exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
assert 'vbc53.cmd' in (out/'msbuild.log').read_text()
assert 'PASS SDK8 Vbc task' in (out/'execute.log').read_text()
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_sdk8_vbc_task_launches_source_net10_compiler=True,net8_emitted_query_application_execution_passed=True,original_sdk10_tasks_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original SDK8 Vbc task -> installed source NET10 vbc53.cmd -> executed NET8 query program')
