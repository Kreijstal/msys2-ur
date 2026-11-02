"""Validate the candidate or installed MSBuild18 payload in fresh consumers."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,xml.etree.ElementTree as E

prefix,out=(Path(p).resolve() for p in sys.argv[1:3]);out.mkdir()
actual=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=actual/'lib/dotnet10/dotnet.exe';native=lambda p:Path(p).resolve().as_posix()
tool=prefix/'lib/dotnet10/build-packs/msbuild-18.3.0-net10-bootstrap';doc=prefix/'share/doc/dotnet-msbuild18-bootstrap';checks=doc/'checks'
manifest=json.loads((doc/'payload-sha256.json').read_text())
for path,digest in manifest.items():assert hashlib.sha256((prefix/path).read_bytes()).hexdigest()==digest,path
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),MSBUILD_EXE_PATH=native(tool/'MSBuild.dll'),MSBUILDUSESERVER='0',MSBUILDDISABLENODEREUSE='1',MSBuildEnableWorkloadResolver='false')
commands=[]
def run(label,command,environment=env):
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=environment,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    commands.append(dict(label=label,command=[str(p) for p in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
    return (out/(label+'.log')).read_text(encoding='utf-8')
assert '18.3.0.11413' in run('version',[host,tool/'MSBuild.dll','-nologo','-version','-noautoresponse'])
assert 'Projekt' in run('german-help',[host,tool/'MSBuild.dll','-nologo','-help','-noautoresponse'],dict(env,DOTNET_CLI_UI_LANGUAGE='de'))
work=out/'owned Unicode λ';work.mkdir();(work/'input.txt').write_text('Grüße 世界 😀\n',encoding='utf-8')
p=E.Element('Project');t=E.SubElement(p,'Target',Name='Build')
E.SubElement(t,'MakeDir',Directories=native(work/'output'))
E.SubElement(t,'Copy',SourceFiles=native(work/'input.txt'),DestinationFiles=native(work/'output/copied.txt'))
E.SubElement(t,'WriteLinesToFile',File=native(work/'receipt.txt'),Lines='$(MSBuildVersion)|$(MSBuildAssemblyVersion)|$(MSBuildRuntimeType)',Overwrite='true')
project=work/'Owned.proj';E.ElementTree(p).write(project,encoding='utf-8',xml_declaration=True)
run('original-default-tasks',[host,tool/'MSBuild.dll',project,'-t:Build','-noautoresponse','-nr:false','-nologo','-v:minimal'])
assert (work/'input.txt').read_bytes()==(work/'output/copied.txt').read_bytes()
assert (work/'receipt.txt').read_text(encoding='utf-8-sig').strip()=='18.3.0|18.0|Core'
run('parallel',[sys.executable,'-X','utf8',checks/'check-parallel.py',tool,out/'parallel'])
consumer=out/'resource-consumer';shutil.copytree(tool,consumer)
for n in ['Check.dll','Check.runtimeconfig.json']:shutil.copyfile(checks/n,consumer/n)
text=run('all-resources',[host,consumer/'Check.dll',checks/'expected-resources.json']);assert '23597' in text
launchers=False
if prefix==actual:
    assert '18.3.0.11413' in run('shell-launcher',[actual.parent/'usr/bin/bash.exe',prefix/'bin/msbuild18-bootstrap','-nologo','-version','-noautoresponse'])
    command=subprocess.list2cmdline([os.environ.get('COMSPEC','cmd.exe')])+' /d /s /c ""'+str(tool/'msbuild18-bootstrap.cmd')+'" -nologo -version -noautoresponse"'
    r=subprocess.run(command,env=dict(env,DOTNET_ROOT=native(actual/'lib/dotnet'),DOTNET_HOST_PATH=native(actual/'lib/dotnet/dotnet.exe')),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',timeout=60)
    (out/'cmd-launcher.log').write_text(r.stdout,encoding='utf-8');assert r.returncode==0 and '18.3.0.11413' in r.stdout,r.stdout
    commands.append(dict(label='cmd-launcher-with-inherited-sdk8-host',command=command,exit_code=r.returncode));launchers=True
(out/'results.json').write_text(json.dumps(dict(commands=commands,payload_files_byte_verified=len(manifest),all_localized_values_verified=23597,actual_default_task_registration_and_unicode_build_passed=True,two_distinct_parallel_processes_verified=True,installed_shell_and_cmd_launchers_verified=launchers,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS MSBuild18 bootstrap payload,default tasks,Unicode,parallel workers and all23597 localized values;installed launchers:',launchers)
