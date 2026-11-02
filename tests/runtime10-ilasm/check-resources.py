"""Exercise native ILAsm with valid COFF section layouts and malformed resources."""
from pathlib import Path
import hashlib
import json
import struct
import subprocess
import sys

root,maintenance,out=(Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(),out
out.mkdir(parents=True)
native_root=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
def native(p):return native_root+'/'+p.resolve().relative_to(root).as_posix()
def version_payload(path):
    data=path.read_bytes();u16=lambda o:struct.unpack_from('<H',data,o)[0];u32=lambda o:struct.unpack_from('<I',data,o)[0]
    coff=u32(0x3c)+4;optional=coff+20;sections=optional+u16(coff+16)
    rva=u32(optional+(112 if u16(optional)==0x20b else 96)+16)
    def offset(rva):
        for i in range(u16(coff+2)):
            s=sections+i*40
            if u32(s+12)<=rva<u32(s+12)+max(u32(s+8),u32(s+16)):return u32(s+20)+rva-u32(s+12)
        raise AssertionError(rva)
    base=offset(rva)
    def entries(r):
        r+=base;return [(u32(r+16+i*8),u32(r+20+i*8)) for i in range(u16(r+12)+u16(r+14))]
    type_node=next(v for k,v in entries(0) if k==16)
    name_node=next(v for k,v in entries(type_node&0x7fffffff) if k==1)
    languages=entries(name_node&0x7fffffff);assert len(languages)==1
    entry=base+languages[0][1];start=offset(u32(entry));return data[start:start+u32(entry+4)]
folder=maintenance/'System.Runtime.CompilerServices.Unsafe'
original=(folder/'native-version.obj').read_bytes()
assert struct.unpack_from('<H',original,2)[0]==2
variants={'llvm-two-sections':original}
# A leading non-resource section reproduces the three-section layout accepted
# by the old reader. Adjust every affected COFF offset and symbol section index.
three=bytearray(original[:20]+b'.debug$S'+bytes(32)+original[20:])
struct.pack_into('<H',three,2,3)
symbols=struct.unpack_from('<I',original,8)[0]
struct.pack_into('<I',three,8,symbols+40)
for index in range(2):
    start=20+40+index*40
    for field in [20,24,28]:
        value=struct.unpack_from('<I',three,start+field)[0]
        if value:struct.pack_into('<I',three,start+field,value+40)
index=0
while index<struct.unpack_from('<I',original,12)[0]:
    at=symbols+40+index*18;section=struct.unpack_from('<h',three,at+12)[0]
    if section>0:struct.pack_into('<h',three,at+12,section+1)
    index+=1+three[at+17]
variants['leading-debug-three-sections']=bytes(three)
bounded=bytearray(original);struct.pack_into('<I',bounded,28,1)
variants['eight-byte-section-name']=bytes(bounded)
bad=bytearray(original)
relocations=struct.unpack_from('<I',original,20+24)[0]
symbol_index=struct.unpack_from('<I',original,relocations+4)[0]
struct.pack_into('<h',bad,symbols+symbol_index*18+12,1)
variants['invalid-symbol-section']=bytes(bad)
variants['truncated-resource']=original[:120]
record=json.loads((maintenance/'source-inputs.json').read_text())['projects']['System.Runtime.CompilerServices.Unsafe']
source=maintenance/('maintenance-packages-'+record['commit'])/next(iter(record['original_sources']))
results={};expected=(folder/'native-version.bin').read_bytes()
for name,data in variants.items():
    directory=out/name;directory.mkdir();obj=directory/'resource.obj';obj.write_bytes(data)
    product=directory/'System.Runtime.CompilerServices.Unsafe.dll'
    command=[native(root/'coreclr-build/ilasm/ilasm.exe'),'-DLL','-DEBUG=OPT','-DET','-INCLUDE='+native(folder/'include'),'-KEY='+native(maintenance/'Microsoft.pubkey'),'-RESOURCE='+native(obj),'-OUTPUT='+native(product),native(source)]
    with (directory/'build.log').open('w') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
    success=name not in {'invalid-symbol-section','truncated-resource'}
    if success:assert r.returncode==0 and version_payload(product)==expected,(name,r.returncode)
    else:assert r.returncode!=0 and 'FAILURE' in (directory/'build.log').read_text(),name
    results[name]=dict(exit_code=r.returncode,expected_success=success,input_sha256=hashlib.sha256(data).hexdigest(),native_version_payload_matches=success)
    print('PASS ILAsm resource case',name,flush=True)
(out/'results.json').write_text(json.dumps(dict(cases=results,complete=True,production_il_changes=0,full_runtime10_complete=False),indent=2)+'\n')
