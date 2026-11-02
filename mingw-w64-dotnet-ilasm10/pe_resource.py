from pathlib import Path
import struct

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
