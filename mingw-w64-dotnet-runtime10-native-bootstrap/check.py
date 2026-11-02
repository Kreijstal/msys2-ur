"""Test the native package directly using original headers and owned processes."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
root=Path(sys.argv[1]).resolve();built=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve();out.mkdir();here=Path(__file__).resolve().parent
installed=Path(sys.argv[4]).resolve() if len(sys.argv)>4 else None
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
layout=out/'native10 λ';layout.mkdir();files={}
for name in ['System.IO.Compression.Native','System.Globalization.Native']:
 candidates=[installed/(name+'.dll')] if installed else list((built/'build').rglob(name+'.dll'));assert len(candidates)==1 and candidates[0].is_file(),(name,candidates)
 shutil.copy2(candidates[0],layout/(name+'.dll'));files[name]=candidates[0]
libs=list((built/'build').rglob('*System.IO.Compression.Native.dll.a'));assert len(libs)==1,libs
source=root/'r/src/native';command=['/clang64/bin/clang',str(here/'inputs/CompressionProbe.c'),'-I'+str(source/'libs/System.IO.Compression.Native'),'-I'+str(source/'external/brotli/c/include'),str(libs[0]),'-o',str(layout/'compression-probe.exe')]
with (out/'compile.log').open('w') as f:r=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT)
assert r.returncode==0,(r.returncode,out/'compile.log')
with (out/'compression.log').open('w') as f:r=subprocess.run([str(layout/'compression-probe.exe')],cwd=layout,stdout=f,stderr=subprocess.STDOUT,timeout=60)
assert r.returncode==0,(r.returncode,out/'compression.log')
# Python ctypes directly calls the exact isolated globalization DLL.
probe=out/'icu.py';probe.write_text('''import ctypes,json,sys
library=ctypes.WinDLL(sys.argv[1]);load=library.GlobalizationNative_LoadICU;load.restype=ctypes.c_int;assert load()==1
version=library.GlobalizationNative_GetICUVersion;version.restype=ctypes.c_int;value=version();assert value!=0
print(json.dumps(dict(original_icu_load_passed=True,icu_version=value)))
''')
with (out/'icu.json').open('w') as f:r=subprocess.run(['/clang64/bin/python.exe',native(probe),native(layout/'System.Globalization.Native.dll')],stdout=f,stderr=subprocess.STDOUT,timeout=30)
assert r.returncode==0,(r.returncode,out/'icu.json')
record=dict(installed_product_checked=installed is not None,compression_roundtrips_levels=[1,6,9],known_crc32_passed=True,brotli_roundtrip_passed=True,original_runtime10_stream_header_used=True,original_icu_load_and_version_passed=True,tested_files_sha256={p.name:sha(p) for p in layout.iterdir() if p.is_file()},full_framework_complete=False,full_dependency_goal_complete=False)
(out/'results.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS native10 original stream ABI,deflate/inflate levels1/6/9,known CRC32,Brotli and direct ICU version')
