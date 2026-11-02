"""Audit original compiler inputs, exact CI-only metadata overlays and produced bytes."""
from pathlib import Path
import hashlib,json,subprocess,sys

source,out=(Path(p).resolve() for p in sys.argv[1:]);name='Microsoft.IdentityModel.Abstractions'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record=json.loads((out/'source-inventory.json').read_text())
native=subprocess.check_output(['cygpath','-am',str(out)],text=True).strip().replace('\\','/')+'/'
target=out/'src'/name;actual={};generated={}
for value in (target/'obj/Release/net8.0/compiler-inputs.txt').read_text(encoding='utf-8-sig').splitlines():
    value=value.replace('\\','/');assert value.lower().startswith(native.lower()),value
    relative=value[len(native):]
    if relative in record['original_cs']:
        wanted=record['ci_version_metadata'].get(relative,record['original_cs'][relative])
        assert sha(out/relative)==wanted,relative;actual[relative]=wanted
    else:
        assert relative in ['src/'+name+'/obj/Release/net8.0/'+name+'.AssemblyInfo.cs','src/'+name+'/obj/Release/net8.0/.NETCoreApp,Version=v8.0.AssemblyAttributes.cs'],relative
        generated[relative]=sha(out/relative)
assert set(actual)==set(record['original_cs']) and len(generated)==2
for relative,digest in record['original_cs'].items():assert sha(source/relative)==digest
for relative,digest in record['prepared_project_metadata'].items():assert sha(out/relative)==digest
record.update(actual_compiler_inputs=actual,generated_sdk_metadata=generated,
 implementation_sha256=sha(target/'bin/Release/net8.0'/(name+'.dll')),
 reference_sha256=sha(target/'obj/Release/net8.0/ref'/(name+'.dll')),
 documentation_sha256=sha(target/'bin/Release/net8.0'/(name+'.xml')))
(out/'source-inventory.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS all nine original compiler items, two SDK metadata files, recorded CI metadata-only overlay and source implementation/reference/XML outputs')
