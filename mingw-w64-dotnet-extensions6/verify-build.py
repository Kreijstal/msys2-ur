"""Gate actual compiler inputs against every unchanged original source/shared file."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

source,prepared=(Path(p).resolve() for p in sys.argv[1:])
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip().replace('\\','/')
source_native=native(source)+'/'
sha=lambda data:hashlib.sha256(data).hexdigest()
records=json.loads((prepared/'source-inventory.json').read_text())
total=0
for name,record in records.items():
    target=prepared/name
    expected=record['original_cs'] | record['shared_cs']
    for relative,digest in expected.items():assert sha((source/relative).read_bytes())==digest,relative
    actual=set();generated=[]
    for line in (target/'obj/Release/net8.0/compiler-inputs.txt').read_text(encoding='utf-8-sig').splitlines():
        path=line.replace('\\','/')
        if path.lower().startswith(source_native.lower()):
            actual.add(path[len(source_native):])
        else:
            own=native(target)+'/'
            assert path.lower().startswith(own.lower()),path
            relative=path[len(own):]
            assert relative in ['SR.Generated.cs','obj/Release/net8.0/Library.AssemblyInfo.cs','obj/Release/net8.0/.NETCoreApp,Version=v8.0.AssemblyAttributes.cs'],relative
            generated.append(relative)
    assert actual==set(expected),(name,actual-set(expected),set(expected)-actual)
    assert len(generated)==3 and 'SR.Generated.cs' in generated
    assert sha((target/'SR.Generated.cs').read_bytes())==record['generated_sr_sha256']
    record['actual_original_compile_items']=sorted(actual)
    record['actual_generated_compile_items']=generated
    record['implementation_sha256']=sha((target/'bin/Release/net8.0'/(name+'.dll')).read_bytes())
    record['reference_sha256']=sha((target/'obj/Release/net8.0/ref'/(name+'.dll')).read_bytes())
    total+=len(actual)
    (target/'source-inventory.json').write_text(json.dumps(record,indent=2)+'\n')
assert total==56
(prepared/'source-inventory.json').write_text(json.dumps(records,indent=2)+'\n')
print('PASS all56 actual unchanged original C# compiler inputs, three generated resource bindings and six SDK metadata files')
