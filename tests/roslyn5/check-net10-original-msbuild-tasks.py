"""Run source SDK10 Csc/Vbc tasks inside source MSBuild18 with NET10 outputs."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as E

task,stage,out=(Path(p).resolve() for p in sys.argv[1:4]);only_vb=sys.argv[4:]==['--only-vb'];assert not sys.argv[4:] or only_vb;out.mkdir()
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip())
host=prefix/'lib/dotnet10/dotnet.exe';tool=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap'
native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),MSBUILD_EXE_PATH=native(stage/'MSBuild.dll'),MSBUILDUSESERVER='0',MSBUILDDISABLENODEREUSE='1',MSBuildEnableWorkloadResolver='false')
commands=[]
def run(label,command,expected=0):
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    commands.append(dict(label=label,command=[str(x) for x in command],exit_code=r.returncode));assert r.returncode==expected,(label,r.returncode)
    return (out/(label+'.log')).read_text(encoding='utf-8')
programs={
 'Csc':('cs','''using System;
public static class Extensions { extension(string text) { public int TwiceLength => text.Length*2; } }
class Program { static void Main() { if("Grüße".TwiceLength!=10)throw new Exception();Console.WriteLine("PASS original SDK10 Csc task, CSharp14 and NET10 Unicode Grüße 世界"); } }
'''),
 'Vbc':('vb','''Imports System
Imports System.Linq
Module Program
 Sub Main()
  Dim q=From n In {1,2,3} Select n*2
  If q.Sum()<>12 Then Throw New Exception("LINQ result")
  Console.WriteLine("PASS original SDK10 Vbc task and NET10 Unicode Grüße 世界")
 End Sub
End Module
''')}
for name,(extension,program) in programs.items():
    if only_vb and name!='Vbc':continue
    folder=out/(name+' λ');folder.mkdir();source=folder/('Program 世界.'+extension);source.write_text(program,encoding='utf-8')
    output=folder/'Application.dll'
    p=E.Element('Project');E.SubElement(p,'UsingTask',TaskName='Microsoft.CodeAnalysis.BuildTasks.'+name,AssemblyFile=native(task))
    ig=E.SubElement(p,'ItemGroup')
    for ref in refs:E.SubElement(ig,'Reference',Include=native(ref))
    t=E.SubElement(p,'Target',Name='Build')
    attrs=dict(Sources=native(source),References='@(Reference)',OutputAssembly=native(output),TargetType='Exe',ToolPath=native(tool),ToolExe=('csc53.cmd' if name=='Csc' else 'vbc53.cmd'),UseSharedCompilation='false',NoConfig='true',NoStandardLib='true',EmitDebugInformation='true',DebugType='portable',Deterministic='true')
    attrs.update(dict(LangVersion='14') if name=='Csc' else dict(VBRuntime='Embed',DefineConstants='_MYTYPE="Empty"',OptionStrict='On',OptionInfer='true'))
    E.SubElement(t,name,**attrs);project=folder/'Compile.proj';E.ElementTree(p).write(project,encoding='utf-8',xml_declaration=True)
    log=run('compile-'+name,[host,stage/'MSBuild.dll',project,'-t:Build','-nr:false','-noautoresponse','-nologo','-v:diag'])
    assert native(task).lower() in log.replace('\\','/').lower(),'Task assembly not observed'
    (folder/'Application.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
    assert 'PASS original SDK10 '+name+' task' in run('execute-'+name,[host,output])
    assert output.with_suffix('.pdb').is_file()
    source.write_text('class Broken { void M() { MissingName(); } }' if name=='Csc' else 'Module Broken\nSub Main()\nMissingName()\nEnd Sub\nEnd Module\n')
    log=run('invalid-'+name,[host,stage/'MSBuild.dll',project,'-t:Build','-nr:false','-noautoresponse','-nologo','-v:minimal'],1)
    assert ('CS0103' if name=='Csc' else 'BC30451') in log
(out/'results.json').write_text(json.dumps(dict(commands=commands,task_sha256=sha(task),msbuild18_sha256=sha(stage/'MSBuild.dll'),verified_languages=['Vbc'] if only_vb else ['Csc','Vbc'],original_sdk10_csc_and_vbc_tasks_executed=not only_vb,csharp14_extension_and_vb_linq_net10_outputs_executed=not only_vb,unicode_paths_outputs_portable_pdb_and_original_error_codes_verified=True,compiler_server_task_path_verified=False,sdk_style_build_verified=False,formal_task_package_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original SDK10 tasks', ['Vbc'] if only_vb else ['Csc','Vbc'],'on source MSBuild18,NET10 execution,Unicode/PDB and invalid-source diagnostics')
