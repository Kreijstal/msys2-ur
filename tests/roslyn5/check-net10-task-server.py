"""Prove original SDK10 tasks start and share their source compiler server."""
from pathlib import Path
import ctypes,json,os,re,shutil,subprocess,sys,uuid,xml.etree.ElementTree as E

task,stage,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe'
native=lambda p:Path(p).resolve().as_posix()
tool=out/'compiler';tool.mkdir();shutil.copytree(prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap',tool/'bincore')
shutil.copyfile(task,tool/task.name)
logs=out/'protocol';logs.mkdir();pipe='codex-sdk10-tasks-'+uuid.uuid4().hex
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),MSBUILD_EXE_PATH=native(stage/'MSBuild.dll'),MSBUILDUSESERVER='0',MSBUILDDISABLENODEREUSE='1',RoslynCommandLineLogFile=native(logs))
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];kernel.OpenProcess.restype=ctypes.c_void_p
kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong];kernel.WaitForSingleObject.restype=ctypes.c_ulong
kernel.QueryFullProcessImageNameW.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)]
kernel.CloseHandle.argtypes=[ctypes.c_void_p]
commands=[];handle=None;pid=None;shutdown=False
def run(label,command):
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    commands.append(dict(label=label,command=[str(x) for x in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
    return (out/(label+'.log')).read_text(encoding='utf-8')
try:
    for name,extension,program in [('Csc','cs','public class SharedCS { public static int Value => 42; }'),('Vbc','vb','Public Module SharedVB\nPublic Function Value() As Integer\nReturn 42\nEnd Function\nEnd Module\n')]:
        source=out/(name+' λ 世界.'+extension);source.write_text(program,encoding='utf-8')
        p=E.Element('Project');E.SubElement(p,'UsingTask',TaskName='Microsoft.CodeAnalysis.BuildTasks.'+name,AssemblyFile=native(tool/task.name))
        ig=E.SubElement(p,'ItemGroup')
        for ref in refs:E.SubElement(ig,'Reference',Include=native(ref))
        t=E.SubElement(p,'Target',Name='Build')
        attrs=dict(Sources=native(source),References='@(Reference)',OutputAssembly=native(out/(name+'.dll')),TargetType='Library',UseSharedCompilation='true',SharedCompilationId=pipe,NoConfig='true',NoStandardLib='true')
        if name=='Vbc':attrs.update(VBRuntime='Embed',DefineConstants='_MYTYPE="Empty"')
        E.SubElement(t,name,**attrs);project=out/(name+'.proj');E.ElementTree(p).write(project,encoding='utf-8',xml_declaration=True)
        text=run(name,[host,stage/'MSBuild.dll',project,'-t:Build','-nr:false','-noautoresponse','-nologo','-v:diag'])
        assert 'CompilerServer: server - server processed compilation' in text,text[-2000:]
        assert 'CompilerServer: server failed' not in text
        assert (out/(name+'.dll')).is_file()
        protocol='\n'.join(p.read_text(encoding='utf-8',errors='replace') for p in logs.glob('*.log'))
        creates={int(s) for s in re.findall(r'Successfully created process with process id (\d+)',protocol)}
        assert len(creates)==1,creates
        if handle is None:
            pid=creates.pop();handle=kernel.OpenProcess(0x00101000,False,pid);assert handle,ctypes.get_last_error()
            size=ctypes.c_ulong(32768);image=ctypes.create_unicode_buffer(size.value)
            assert kernel.QueryFullProcessImageNameW(handle,0,image,ctypes.byref(size)),ctypes.get_last_error()
            assert Path(image.value).resolve()==host.resolve(),image.value
        assert kernel.WaitForSingleObject(handle,0)==258
    run('shutdown',[host,tool/'bincore/VBCSCompiler.dll','-shutdown','-pipename:'+pipe])
    assert kernel.WaitForSingleObject(handle,30000)==0;shutdown=True
finally:
    if not shutdown:
        try:run('cleanup-shutdown',[host,tool/'bincore/VBCSCompiler.dll','-shutdown','-pipename:'+pipe])
        except Exception:pass
        if handle:assert kernel.WaitForSingleObject(handle,45000)==0,'owned server still live'
    if handle:kernel.CloseHandle(handle)
(out/'results.json').write_text(json.dumps(dict(commands=commands,owned_server_process_id=pid,owned_server_image_verified=True,original_tasks_automatically_start_and_share_one_server=True,completed_server_requests=2,command_line_fallback_absent=True,owned_server_shutdown_verified=True,formal_task_package_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original SDK10 Csc/Vbc tasks auto-start/share one source NET10 compiler server,no fallback,owned process identity and shutdown')
