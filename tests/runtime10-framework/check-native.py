"""Execute native10 compression/globalization with the actual source10 managed graph."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
plan=Path(sys.argv[1]).resolve();native_build=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve();out.mkdir();here=Path(__file__).resolve().parent
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
status=json.loads((plan/'build-status.json').read_text());assert 'System.IO.Compression' in status
layout=out/'native managed10 λ';layout.mkdir()
for name in ['coreclr.dll','clrjit.dll','mscorrc.dll','clretwrc.dll']:shutil.copy2(Path('/clang64/lib/dotnet-bootstrap10/coreclr/10.0.5')/name,layout/name)
for name in ['corerun.exe','System.Private.CoreLib.dll']:shutil.copy2(Path('/clang64/lib/dotnet-bootstrap10/corelib/10.0.5')/name,layout/name)
for name,item in status.items():
 if item['kind']!='stub':
  source=plan/'lib'/(name+'.dll');assert sha(source)==item['output_sha256'];shutil.copy2(source,layout/source.name)
for name in ['System.IO.Compression.Native.dll','System.Globalization.Native.dll']:
 files=list((native_build/'build').rglob(name));assert len(files)==1,(name,files);shutil.copy2(files[0],layout/name)
refs=sorted(layout.glob('*.dll'));args=['/nostdlib+','/target:exe','/langversion:preview','/out:"'+native(layout/'NativeFrameworkProbe.dll')+'"']+['/reference:"'+native(p)+'"' for p in refs if p.name not in ['coreclr.dll','clrjit.dll','mscorrc.dll','clretwrc.dll','System.IO.Compression.Native.dll','System.Globalization.Native.dll']]+['"'+native(here/'inputs/NativeFrameworkProbe.cs')+'"'];rsp=out/'compile.rsp';rsp.write_text('\n'.join(args)+'\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_TELEMETRY_OPTOUT='1')
with (out/'compile.log').open('w') as f:r=subprocess.run(['/clang64/lib/dotnet/dotnet.exe',native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap/CompilerHost.dll')),'-noconfig','@'+native(rsp)],env=env,stdout=f,stderr=subprocess.STDOUT)
assert r.returncode==0,(r.returncode,out/'compile.log')
win=lambda p:native(p).replace('/','\\');command=[str(layout/'corerun.exe'),'-c',win(layout),win(layout/'NativeFrameworkProbe.dll'),win(layout/'System.Globalization.Native.dll')]
with (out/'execute.log').open('w') as f:r=subprocess.run(command,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=120)
record=dict(command=command,exit_code=r.returncode,matching_source10_native_compression_and_globalization_execution_passed=r.returncode==0,managed_libraries_available=len([n for n in status if not n.startswith('stub:')]),tested_files_sha256={p.name:sha(p) for p in layout.iterdir() if p.is_file()},full_framework_complete=False,full_dependency_goal_complete=False)
(out/'results.json').write_text(json.dumps(record,indent=2)+'\n');assert r.returncode==0,(r.returncode,out/'execute.log');print('PASS source10 GZip/Deflate/Brotli/Unicode ZIP, direct original ICU loading/version and managed German/Turkish/normalization probes')
