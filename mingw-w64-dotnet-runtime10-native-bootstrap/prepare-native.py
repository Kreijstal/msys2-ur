"""Keep the original native-library graph and isolate generated version resources."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile,shutil,difflib
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(exist_ok=True)
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
archive=root/'arcade-runtime10-4bf37ce6.tar.gz';assert sha(archive)=='82f5f6dd63c0dcf3c0fc49b282207db5d889d9cc0939589d43b16c7fcfdf7d66'
resources=out/'resources';resources.mkdir(exist_ok=True)
with tarfile.open(archive) as tar:
 m=next(m for m in tar if m.name.endswith('/src/Microsoft.DotNet.Arcade.Sdk/tools/NativeVersion.rc'));rc=tar.extractfile(m).read();adapted_rc=rc.decode()
 for macro in ['VER_FILEDESCRIPTION_STR','VER_INTERNALNAME_STR','VER_ORIGINALFILENAME_STR']:adapted_rc=adapted_rc.replace(macro,'NATIVE_RC_STRING('+macro+')')
 adapted_rc='#define NATIVE_RC_STRING_IMPL(x) #x\n#define NATIVE_RC_STRING(x) NATIVE_RC_STRING_IMPL(x)\n'+adapted_rc
 (resources/'NativeVersion.rc').write_text(adapted_rc)
header=(root/'r/artifacts/obj/_version.h').read_text();before=header
lines=[]
for line in header.splitlines():
 if line.startswith('#define VER_FILEDESCRIPTION_STR '):lines+=['#ifndef VER_FILEDESCRIPTION_STR',line,'#endif']
 else:lines.append(line)
(resources/'_Version.h').write_text('\n'.join(lines)+'\n')
wrapper=out/'source';wrapper.mkdir(exist_ok=True);src=root/'r'
local=out/'native-source';local.mkdir(exist_ok=True)
shutil.copytree(src/'src/native/libs',local/'libs')
changes={}
for name in ['System.Globalization.Native','System.IO.Compression.Native']:
 file=local/'libs'/name/'CMakeLists.txt';original=file.read_text();needle='        install (FILES $<TARGET_PDB_FILE:'+name+'> DESTINATION .)';assert original.count(needle)==1
 updated=original.replace(needle,'        if(MSVC)\n'+needle+'\n        endif()');file.write_text(updated)
 changes['src/native/libs/'+name+'/CMakeLists.txt']=dict(original_sha256=hashlib.sha256(original.encode()).hexdigest(),ported_sha256=sha(file),change='Install PDB only when using an MSVC-compatible linker.')
file=local/'libs/System.IO.Compression.Native/zlib_allocator_win.c';original=file.read_text()
anchor='#include <Windows.h>\n';assert original.count(anchor)==1
compat='\n// Windows SDK winnt.h value; older MinGW headers omit this constant.\n#ifndef FAST_FAIL_HEAP_METADATA_CORRUPTION\n#define FAST_FAIL_HEAP_METADATA_CORRUPTION 50\n#endif\n'
updated=original.replace(anchor,anchor+compat);file.write_text(updated)
changes['src/native/libs/System.IO.Compression.Native/zlib_allocator_win.c']=dict(original_sha256=hashlib.sha256(original.encode()).hexdigest(),ported_sha256=sha(file),change='Supply the exact Windows SDK fail-fast code when the headers omit it; allocator and fail-fast call unchanged.',source='https://github.com/microsoft/win32metadata/blob/main/generation/WinSDK/RecompiledIdlHeaders/um/winnt.h')
(out/'native-libs-mingw.patch').write_text(''.join(''.join(difflib.unified_diff((src/name).read_text().splitlines(True),(local/'libs'/Path(name).relative_to('src/native/libs')).read_text().splitlines(True),fromfile='a/'+name,tofile='b/'+name)) for name in changes))
# Same top-level setup as upstream libs/CMakeLists.txt. Its root-only block is
# skipped when imported below, allowing a private generated resource location.
text='\n'.join(['cmake_minimum_required(VERSION 3.20)','project(LibsNative C)',f'include("{native(src/"eng/native/configurepaths.cmake")}")',f'include("{native(src/"eng/native/configurecompiler.cmake")}")',f'add_subdirectory("{native(src/"src/native/minipal")}" minipal)',f'set(VERSION_FILE_RC_PATH "{native(resources/"NativeVersion.rc")}")',f'add_subdirectory("{native(local/"libs")}" libs)',''])
(wrapper/'CMakeLists.txt').write_text(text)
record=dict(runtime_commit='081d220c0a773ffb7c6bea6b48727833576a65ef',original_libs_cmake_sha256=sha(src/'src/native/libs/CMakeLists.txt'),original_arcade_native_rc_sha256=hashlib.sha256(rc).hexdigest(),adapted_rc_sha256=sha(resources/'NativeVersion.rc'),rc_adapter='Stringify the three per-library name macros for llvm-windres command-line define handling.',original_generated_version_header_sha256=hashlib.sha256(before.encode()).hexdigest(),private_version_header_sha256=sha(resources/'_Version.h'),private_cmake_wrapper_sha256=sha(wrapper/'CMakeLists.txt'),native_compatibility_c_files=1,native_executable_behavior_replacements=0,cmake_port_files=changes,native_source_copy=str(local/'libs'),version_header_adapter='Keep per-library VER_FILEDESCRIPTION_STR from original CMake compile definitions; remaining generated version fields unchanged.',full_framework_complete=False)
(out/'source-inputs.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS private native version-resource location, exact original Arcade RC and original native CMake setup')
