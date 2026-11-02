"""Match targeting metadata to the actual source-built shared-framework files.

The pack-directory alias is not the file version of an implementation DLL.
Pure forwarding shims can retain their own generated file versions.
"""
import ctypes
from ctypes import wintypes
from pathlib import Path
import sys
import xml.etree.ElementTree as E

root,runtime=map(Path,sys.argv[1:])
version_api=ctypes.WinDLL('version',use_last_error=True)
version_api.GetFileVersionInfoSizeW.argtypes=[wintypes.LPCWSTR,ctypes.POINTER(wintypes.DWORD)]
version_api.GetFileVersionInfoSizeW.restype=wintypes.DWORD
version_api.GetFileVersionInfoW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID]
version_api.GetFileVersionInfoW.restype=wintypes.BOOL
version_api.VerQueryValueW.argtypes=[wintypes.LPCVOID,wintypes.LPCWSTR,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(wintypes.UINT)]
version_api.VerQueryValueW.restype=wintypes.BOOL

def file_version(path):
    if not path.is_file():raise SystemExit('Missing built runtime file: '+str(path))
    ignored=wintypes.DWORD();size=version_api.GetFileVersionInfoSizeW(str(path),ctypes.byref(ignored))
    if not size:raise ctypes.WinError(ctypes.get_last_error())
    data=ctypes.create_string_buffer(size)
    if not version_api.GetFileVersionInfoW(str(path),0,size,data):raise ctypes.WinError(ctypes.get_last_error())
    ptr=ctypes.c_void_p();length=wintypes.UINT()
    if not version_api.VerQueryValueW(data,'\\',ctypes.byref(ptr),ctypes.byref(length)):raise ctypes.WinError(ctypes.get_last_error())
    assert length.value>=13*4,path
    fixed=ctypes.cast(ptr,ctypes.POINTER(wintypes.DWORD*13)).contents
    assert fixed[0]==0xFEEF04BD,path
    ms,ls=fixed[2],fixed[3]
    return '.'.join(str(v) for v in (ms>>16,ms&0xffff,ls>>16,ls&0xffff))

for data in root.glob('*/data'):
    tree=E.parse(data/'FrameworkList.xml');versions={};changed=0
    for item in tree.getroot().findall('File'):
        if item.get('Type')!='Managed':continue
        name=item.get('AssemblyName');actual=file_version(runtime/(name+'.dll'))
        versions[name+'.dll']=actual
        changed+=item.get('FileVersion')!=actual
        item.set('FileVersion',actual)
    assert versions,data
    E.indent(tree);tree.write(data/'FrameworkList.xml',encoding='utf-8',xml_declaration=True)
    lines=[]
    for line in (data/'PlatformManifest.txt').read_text().splitlines():
        fields=line.split('|');assert len(fields)==4,(data,line)
        fields[3]=versions[fields[0]];lines.append('|'.join(fields))
    assert len(lines)==len(versions),(data,len(lines),len(versions))
    (data/'PlatformManifest.txt').write_text('\n'.join(lines)+'\n')
    print(f'{data.parent.name}: verified {len(versions)} managed file versions against runtime PE metadata; corrected {changed}')
