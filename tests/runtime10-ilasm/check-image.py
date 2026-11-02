"""Check the actual Windows native ILAsm image and pinned port inputs."""
from pathlib import Path
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import struct
import sys

root=Path(sys.argv[1]);here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record=json.loads((here/'port-source-inputs.json').read_text())
core_manifest=here/'coreclr-port-source-inputs.json'
assert sha(core_manifest)==record['extends_coreclr_port_manifest_sha256']
core=json.loads(core_manifest.read_text())
for source in [core,record]:
    for name,item in source['changed_files'].items():assert sha(root/'r'/name)==item['ported_sha256'],name
for name,digest in record['patches'].items():assert sha(here/name)==digest,name
image=root/'coreclr-build/ilasm/ilasm.exe';data=image.read_bytes()
u16=lambda o:struct.unpack_from('<H',data,o)[0]
u32=lambda o:struct.unpack_from('<I',data,o)[0]
coff=u32(0x3c)+4;optional=coff+20
assert u16(coff)==0x8664 and u16(optional)==0x20b
assert not u16(coff+18)&0x2000
sections=optional+u16(coff+16)
def offset(rva):
    for i in range(u16(coff+2)):
        s=sections+i*40
        if u32(s+12)<=rva<u32(s+12)+max(u32(s+8),u32(s+16)):return u32(s+20)+rva-u32(s+12)
    raise AssertionError(rva)
debug_rva=u32(optional+112+6*8);debug_size=u32(optional+112+6*8+4)
assert debug_rva and debug_size%28==0
cet=False
for i in range(debug_size//28):
    start=offset(debug_rva)+i*28
    if u32(start+12)==20:
        assert u32(start+16)>=4;cet=bool(u32(u32(start+24))&1)
assert cet,'Missing CET compatibility marker'
version=C.WinDLL('version',use_last_error=True)
version.GetFileVersionInfoSizeW.argtypes=[W.LPCWSTR,C.POINTER(W.DWORD)]
version.GetFileVersionInfoW.argtypes=[W.LPCWSTR,W.DWORD,W.DWORD,C.c_void_p]
version.VerQueryValueW.argtypes=[C.c_void_p,W.LPCWSTR,C.POINTER(C.c_void_p),C.POINTER(W.UINT)]
size=version.GetFileVersionInfoSizeW(str(image),None);assert size
buffer=C.create_string_buffer(size);assert version.GetFileVersionInfoW(str(image),0,size,buffer)
pointer=C.c_void_p();length=W.UINT();assert version.VerQueryValueW(buffer,'\\',C.byref(pointer),C.byref(length))
fixed=struct.unpack('<13I',C.string_at(pointer,52));assert fixed[0]==0xfeef04bd
file_version='.'.join(str(x) for x in [fixed[2]>>16,fixed[2]&65535,fixed[3]>>16,fixed[3]&65535])
assert file_version=='10.0.526.11800',file_version
result=dict(native_image_sha256=sha(image),amd64=True,cet_compatible=True,file_version=file_version,
            original_coreclr_port_files_verified=len(core['changed_files']),additional_native_patch_files_verified=len(record['changed_files']),
            full_runtime10_complete=False,formal_ilasm_package_installed=False)
(root/'ilasm-image-results.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS source native ILAsm AMD64/CET/version and all frozen CoreCLR plus additional source port hashes')
