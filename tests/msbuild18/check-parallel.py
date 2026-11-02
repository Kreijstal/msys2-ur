"""Exercise source MSBuild worker startup, pipe handshakes and parallel projects."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as E

stage,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';native=lambda p:Path(p).resolve().as_posix()
task_source=out/'ReceiptTask.cs'
task_source.write_text('''public sealed class ReceiptTask : Microsoft.Build.Utilities.Task {
 public string Output { get; set; }
 public string Nodes { get; set; }
 public string Label { get; set; }
 public override bool Execute() {
  System.IO.File.WriteAllText(Output, System.Environment.ProcessId + "|" + Nodes + "|" + Label);
  return true;
 }
}''',encoding='utf-8')
task=out/'ReceiptTask.dll'
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'))
assert len(refs)==167
rsp=out/'receipt.rsp'
rsp.write_text('\n'.join(['/nostdlib+','/target:library','/out:"'+native(task)+'"']+['/reference:"'+native(p)+'"' for p in refs+[stage/'Microsoft.Build.Framework.dll',stage/'Microsoft.Build.Utilities.Core.dll']]+['"'+native(task_source)+'"'])+'\n')
compile_command=[host,prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll','-noconfig','@'+native(rsp)]
with (out/'receipt-compile.log').open('w',encoding='utf-8') as log:
    compiled=subprocess.run(compile_command,stdout=log,stderr=subprocess.STDOUT,timeout=60)
assert compiled.returncode==0,compiled.returncode
for index in range(2):
    p=E.Element('Project');pg=E.SubElement(p,'PropertyGroup');E.SubElement(pg,'OwnedOutput').text=native(out/('child'+str(index)+'.txt'))
    E.SubElement(p,'UsingTask',TaskName='Microsoft.Build.Tasks.Exec',AssemblyFile=native(stage/'Microsoft.Build.Tasks.Core.dll'))
    E.SubElement(p,'UsingTask',TaskName='ReceiptTask',AssemblyFile=native(task))
    t=E.SubElement(p,'Target',Name='Run');E.SubElement(t,'Exec',Command='"'+native(prefix/'bin/python.exe')+'" -c "import time; time.sleep(1)"')
    E.SubElement(t,'ReceiptTask',Output='$(OwnedOutput)',Nodes='$(MSBuildNodeCount)',Label='child'+str(index)+' Ω')
    E.ElementTree(p).write(out/('child'+str(index)+'.proj'),encoding='utf-8',xml_declaration=True)
p=E.Element('Project');ig=E.SubElement(p,'ItemGroup')
for index in range(2):E.SubElement(ig,'Child',Include=native(out/('child'+str(index)+'.proj')))
E.SubElement(p,'UsingTask',TaskName='Microsoft.Build.Tasks.MSBuild',AssemblyFile=native(stage/'Microsoft.Build.Tasks.Core.dll'))
t=E.SubElement(p,'Target',Name='Build');E.SubElement(t,'MSBuild',Projects='@(Child)',Targets='Run',BuildInParallel='true')
E.ElementTree(p).write(out/'Parent.proj',encoding='utf-8',xml_declaration=True)
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),MSBUILD_EXE_PATH=native(stage/'MSBuild.dll'),MSBUILDDISABLENODEREUSE='1',MSBUILDUSESERVER='0',MSBuildEnableWorkloadResolver='false')
command=[host,stage/'MSBuild.dll',out/'Parent.proj','-t:Build','-m:2','-nr:false','-noautoresponse','-nologo','-v:minimal']
with (out/'execute.log').open('w',encoding='utf-8') as log:result=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
assert result.returncode==0,result.returncode
receipts=[(out/('child'+str(i)+'.txt')).read_text(encoding='utf-8-sig').strip().split('|') for i in range(2)]
assert all(r[1]=='2' for r in receipts),receipts
assert len({r[0] for r in receipts})==2,receipts
(out/'results.json').write_text(json.dumps(dict(command=[str(x) for x in command],exit_code=0,receipt_compile_command=[str(x) for x in compile_command],receipt_task_sha256=hashlib.sha256(task.read_bytes()).hexdigest(),receipts=receipts,two_distinct_worker_processes_verified=True,original_source_pipe_handshake_and_parallel_build_passed=True,node_reuse_disabled=True,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS source MSBuild18 parallel build,2 distinct processes,original pipe handshake and real Exec tasks')
