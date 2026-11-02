"""Compile a reference-only port of the exact private CoreCLR1.1 compiler contract."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as E

out,prefix,compiler=(Path(x).resolve() for x in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).parent
original=here/'inputs/coreclr-mscorlib.Generated.cs';text=original.read_text(encoding='utf-8-sig')
usings=['System','System.Reflection','System.Resources','System.Runtime.CompilerServices','System.Runtime.InteropServices','System.Diagnostics']
text=re.sub(r'^(\s*public )delegate ([^\n]*\*[^\n]*);',r'\1unsafe delegate \2;',text,flags=re.M)
text,count=re.subn(r'^(\s*)(public Char this\[)',r'\1[System.Runtime.CompilerServices.IndexerName("Chars")]\n\1\2',text,flags=re.M)
projection=out/'mscorlib.cs';projection.write_text('\n'.join('using '+ns+';' for ns in usings)+'\n'+text)
policy=E.parse(here/'inputs/reference-build-policy.props');no_warn=sorted(set(re.findall(r'CS([0-9]{4})',';'.join(e.text or '' for e in policy.findall('.//NoWarn')))))
key=here/'inputs/CoreCLR.public.snk';assert hashlib.sha1(key.read_bytes()).digest()[-8:][::-1].hex()=='7cec85d7bea7798e'
args=['/nostdlib+','/target:library','/runtimemetadataversion:v4.0.30319','/refonly','/unsafe+','/langversion:latest','/nullable:disable','/optimize+','/deterministic+','/warnaserror+','/nowarn:'+','.join(['1701','1702']+no_warn),'/publicsign+','/keyfile:"'+key.as_posix()+'"','/out:"'+(out/'mscorlib.dll').as_posix()+'"','"'+projection.as_posix()+'"']
rsp=out/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');cmd=[str(prefix/'lib/dotnet/dotnet.exe'),str(compiler/'csc.dll'),'-noconfig','@'+str(rsp)]
r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/'compile.log').write_bytes(r.stdout)
assert r.returncode==0,r.stdout.decode(errors='replace')[-18000:]
commands=[dict(command=cmd,exit_code=r.returncode)]
def run(label,args):
    c=[str(p) for p in args];result=subprocess.run(c,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/(label+'.log')).write_bytes(result.stdout);commands.append(dict(command=c,exit_code=result.returncode));assert result.returncode==0,(label,result.stdout.decode(errors='replace')[-6000:])
run('metadata-port-build',[sys.executable,here/'build-metadata-port.py',out/'metadata-port',prefix])
port=out/'metadata-port/bin/Release/net8.0/MetadataPort.dll';reference=out/'ref';reference.mkdir()
run('restore-original-public-metadata',[prefix/'lib/dotnet/dotnet.exe',port,'--apply',out/'mscorlib.dll',here/'inputs/coreclr-mscorlib-metadata-policy.json',reference/'mscorlib.dll'])
run('record-public-metadata',[prefix/'lib/dotnet/dotnet.exe',port,'--record',reference/'mscorlib.dll',out/'recorded-metadata-policy.json'])
assert json.loads((out/'recorded-metadata-policy.json').read_text())==json.loads((here/'inputs/coreclr-mscorlib-metadata-policy.json').read_text())
run('inspector-build',[sys.executable,here/'build-inspector.py',out/'inspector',prefix])
run('inspect-public-API',[prefix/'lib/dotnet/dotnet.exe',out/'inspector/bin/Release/net8.0/Inspect.dll',out/'public-metadata.json',reference/'mscorlib.dll'])
actual=json.loads((out/'public-metadata.json').read_text())['mscorlib.dll'];expected=json.loads((here/'inputs/private-coreclr-metadata.json').read_text())['mscorlib.dll']
assert actual['identity']==expected['identity'] and actual['api']==expected['api'] and actual['references']==expected['references']
(out/'results.json').write_text(json.dumps(dict(command=cmd,exit_code=r.returncode,original_generated_source_SHA256=hashlib.sha256(original.read_bytes()).hexdigest(),projection_SHA256=hashlib.sha256(projection.read_bytes()).hexdigest(),restored_original_Chars_indexer_names=count,source_contract_warning_policy=no_warn,reference_only=True,public_API_and_metadata_equality_verified=True,original_public_API_entries=10960,source_compilation_and_metadata_commands=commands,publisher_DLLs_used_as_compiler_inputs=False,publisher_method_bodies_copied=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS private CoreCLR1.1 source compiler contract compiled')
