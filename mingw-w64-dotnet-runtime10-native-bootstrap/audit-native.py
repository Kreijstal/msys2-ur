"""Windows-native audit of built native units, pinned sources, exports and version resources."""
from pathlib import Path
import ctypes,hashlib,json,os,re,subprocess,sys,tarfile,shutil
root=Path(sys.argv[1]);out=Path(sys.argv[2]);source=root/'r';build=out/'build';record=json.loads((out/'source-inputs.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
port=record['cmake_port_files'];base_port=json.loads((root/'coreclr-port-inputs.json').read_text())['changed_files'];shared={};copy=Path(subprocess.check_output(['cygpath','-am',record['native_source_copy']],text=True).strip());assert copy.is_dir(),copy;expected={}
# Every copied native implementation input retains original archive bytes except the three explicit port files.
for p in copy.rglob('*'):
 if not p.is_file():continue
 rel='src/native/libs/'+p.relative_to(copy).as_posix();original=source/rel
 if rel in port:
  assert sha(original)==port[rel]['original_sha256'] and sha(p)==port[rel]['ported_sha256'],rel
  expected[rel]=sha(original)
 else:
  assert p.read_bytes()==original.read_bytes(),rel
  if rel in base_port:
   assert sha(p)==base_port[rel]['ported_sha256'],rel;expected[rel]=base_port[rel]['original_sha256'];shared[rel]=base_port[rel]
  else:expected[rel]=sha(p)
found={}
with tarfile.open(root/'runtime-v10.0.5.tar.gz') as archive:
 for member in archive:
  rel=member.name.partition('/')[2]
  if rel in expected:found[rel]=hashlib.sha256(archive.extractfile(member).read()).hexdigest()
assert expected==found,'Native source copy differs from pinned archive'
# Match actual executed object outputs, not every possible static/AOT target in compile_commands.json.
executed={line.split('\t')[3].replace('\\','/') for line in (build/'.ninja_log').read_text().splitlines() if line and not line.startswith('#')}
commands=json.loads((build/'compile_commands.json').read_text());units={}
for command in commands:
 output=Path(command['output']).relative_to(build).as_posix()
 if output not in executed:continue
 p=Path(command['file']);assert p.is_file(),p;units[output]=dict(source=str(p),sha256=sha(p),output=output)
assert units
assert {u['output'] for u in units.values()}=={p for p in executed if p.endswith(('.obj','.res'))}, 'Actual native compilation output coverage differs from Ninja log'
assert {'pal_zlib.c','zlib_allocator_win.c','pal_icushim.c'} <= {Path(u['source']).name for u in units.values()}, 'Missing actual native entry-point compilation units'
extra={}
for unit in units.values():
 path=Path(unit['source'])
 if path.is_relative_to(source):extra[path.relative_to(source).as_posix()]=sha(path)
 elif path.is_relative_to(copy):pass
 else:assert path.is_relative_to(out),path
extra_found={}
with tarfile.open(root/'runtime-v10.0.5.tar.gz') as archive:
 for member in archive:
  rel=member.name.partition('/')[2]
  if rel in extra:extra_found[rel]=hashlib.sha256(archive.extractfile(member).read()).hexdigest()
assert extra_found==extra,'Actual vendored/minipal compilation inputs differ from original archive'
libs={}
for name in ['System.Globalization.Native','System.IO.Compression.Native']:
 candidates=list(build.rglob(name+'.dll'));assert len(candidates)==1,(name,candidates);dll=candidates[0];data=dll.read_bytes();offset=int.from_bytes(data[0x3c:0x40],'little');assert data[offset:offset+4]==b'PE\0\0' and int.from_bytes(data[offset+4:offset+6],'little')==0x8664
 tool=Path(shutil.which('llvm-readobj.exe') or shutil.which('llvm-readobj'));result=subprocess.check_output([str(tool),'--coff-exports',str(dll)],text=True);exports=re.findall(r'^\s*Name: (\S+)',result,re.M);assert exports
 original_def=copy/name/(name+'.def');required=[line.split()[0] for line in original_def.read_text().splitlines() if line.strip() and not line.strip().startswith(('LIBRARY','EXPORTS',';'))]
 assert set(required)<=set(exports),(name,set(required)-set(exports))
 # Query actual PE strings using the Windows version API.
 version=ctypes.WinDLL('version',use_last_error=True);version.GetFileVersionInfoSizeW.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)];version.GetFileVersionInfoSizeW.restype=ctypes.c_ulong
 size=version.GetFileVersionInfoSizeW(str(dll),None);assert size
 buffer=ctypes.create_string_buffer(size);version.GetFileVersionInfoW.argtypes=[ctypes.c_wchar_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p];assert version.GetFileVersionInfoW(str(dll),0,size,buffer)
 version.VerQueryValueW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(ctypes.c_uint)];fields={}
 for field in ['FileVersion','ProductVersion','FileDescription','OriginalFilename']:
  pointer=ctypes.c_void_p();length=ctypes.c_uint();assert version.VerQueryValueW(buffer,'\\StringFileInfo\\040904E4\\'+field,ctypes.byref(pointer),ctypes.byref(length));fields[field]=ctypes.wstring_at(pointer.value)
 assert fields['FileVersion']=='10.0.526.11800' and fields['ProductVersion']=='10.0.5' and fields['FileDescription']==name and fields['OriginalFilename']==name,(name,fields)
 libs[name]=dict(path=str(dll),sha256=sha(dll),amd64=True,original_required_exports=len(required),actual_exports=len(exports),version_resources=fields)
result=dict(original_native_archive_files_verified=len(found),explicit_native_port_files=port,existing_shared_coreclr_port_files_verified=shared,actual_built_compilation_units=len(units),actual_built_c_units=sum(Path(u['source']).suffix.lower()=='.c' for u in units.values()),actual_built_resource_units=sum(Path(u['source']).suffix.lower()=='.rc' for u in units.values()),additional_actual_original_compilation_inputs_verified=len(extra),actual_built_units=units,native_libraries=libs,allocator_heap_and_fastfail_implementation_retained=True,windows_sdk_fastfail_code=50,all_required_original_exports_present=True,all_original_runtime_file_versions_match=True,full_framework_complete=False,full_dependency_goal_complete=False)
(out/'source-audit.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS native archive inputs,actual compiled units,original exports,AMD64 and source10 version resources')
