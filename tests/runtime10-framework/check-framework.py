"""Exercise the complete managed graph with installed source CLR/native libraries."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys

plan=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir()
here=Path(__file__).resolve().parent
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
status=json.loads((plan/'build-status.json').read_text())
assert len(status)==190 and sum(r['kind']!='stub' for r in status.values())==171
layout=out/'complete CLR10 λ';layout.mkdir()
origins={}
def copy(source):
 target=layout/source.name;shutil.copy2(source,target)
 assert sha(target)==sha(source)
 origins[target.name]=dict(source=str(source),sha256=sha(source))
for name in ['coreclr.dll','clrjit.dll','mscorrc.dll','clretwrc.dll']:
 copy(Path('/clang64/lib/dotnet-bootstrap10/coreclr/10.0.5')/name)
for name in ['corerun.exe','System.Private.CoreLib.dll']:
 copy(Path('/clang64/lib/dotnet-bootstrap10/corelib/10.0.5')/name)
for name in ['System.IO.Compression.Native.dll','System.Globalization.Native.dll']:
 copy(Path('/clang64/lib/dotnet-bootstrap10/native-libraries/10.0.5')/name)
for name,item in status.items():
 if item['kind']=='stub':continue
 file=plan/'lib'/(name+'.dll');assert sha(file)==item['output_sha256'],name
 copy(file)
managed=[layout/name for name in origins if name.endswith('.dll') and name not in {
 'coreclr.dll','clrjit.dll','mscorrc.dll','clretwrc.dll',
 'System.IO.Compression.Native.dll','System.Globalization.Native.dll'}]
assert len(managed)==172
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),
 DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_TELEMETRY_OPTOUT='1')
cases={}
for case,source in [('native','NativeFrameworkProbe.cs'),('framework','CompleteFrameworkProbe.cs'),('javascript','JavaScriptWindowsProbe.cs')]:
 if len(sys.argv)>3 and case!=sys.argv[3]:continue
 product=layout/(case+'.dll');rsp=out/(case+'.rsp')
 args=['/nostdlib+','/target:exe','/langversion:preview','/nullable:enable',
  '/out:"'+native(product)+'"']+['/reference:"'+native(p)+'"' for p in managed]
 args+=['"'+native(here/'inputs'/source)+'"'];rsp.write_text('\n'.join(args)+'\n')
 command=['/clang64/lib/dotnet/dotnet.exe',native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap/CompilerHost.dll')),'-noconfig','@'+native(rsp)]
 with (out/(case+'-build.log')).open('w') as log:
  compiled=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
 assert compiled.returncode==0,(case,compiled.returncode,out/(case+'-build.log'))
 win=lambda p:native(p).replace('/','\\')
 command=[str(layout/'corerun.exe'),'-c',win(layout),win(product)]
 if case=='native':command.append(win(layout/'System.Globalization.Native.dll'))
 with (out/(case+'-execution.log')).open('w') as log:
  executed=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 cases[case]=dict(command=command,exit_code=executed.returncode,
  build_exit_code=compiled.returncode,source_sha256=sha(here/'inputs'/source),
  product_sha256=sha(product))
assert cases, 'Optional case must be native, framework or javascript'
record=dict(managed_implementation_assemblies=172,private_seed_assemblies_shipped=0,
 installed_native_package_bytes_used=True,cases=cases,tested_files=origins,
 all_cases_passed=all(c['exit_code']==0 for c in cases.values()),
 full_runtime_compatibility_verified=False,full_sdk10_built=False,
 powershell76_built=False,full_dependency_goal_complete=False)
(out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
assert record['all_cases_passed'],(cases,out)
print('PASS complete 172-assembly managed graph with installed source CLR/native packages')
