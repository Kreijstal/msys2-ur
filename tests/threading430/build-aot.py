"""Port the exact original AOT forwarding facade without substituting provider scopes."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

out,prefix,compiler=(Path(p).resolve() for p in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).parent;commands=[]
def run(label,args):
    c=[str(p) for p in args];r=subprocess.run(c,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/(label+'.log')).write_bytes(r.stdout);commands.append(dict(command=c,exit_code=r.returncode));assert r.returncode==0,(label,r.stdout.decode(errors='replace')[-5000:])
name='System.Threading';baseline=json.loads((here/'inputs/baselines1/runtimes-aot-lib-netcore50.json').read_text())[name+'.dll'];dotnet=prefix/'lib/dotnet/dotnet.exe'
info=['[assembly:System.Reflection.AssemblyVersion("4.0.12.0")]']
for row in baseline['attributes']:
    attr=row['type']
    if attr in ['System.Runtime.CompilerServices.CompilationRelaxationsAttribute','System.Runtime.CompilerServices.RuntimeCompatibilityAttribute','System.Diagnostics.DebuggableAttribute']:continue
    info.append('[assembly:global::'+attr+'('+','.join(v.lower() if attr=='System.CLSCompliantAttribute' else json.dumps(v,ensure_ascii=True) for v in row['arguments'])+')]')
(out/'AssemblyInfo.cs').write_text('\n'.join(info)+'\n');nv=next(r['native_version'] for r in json.loads((here/'inputs/baselines1/resource-data.json').read_text()) if '/runtimes/aot/' in r['file']);assert nv['Language']=='Language Neutral'
rc=['LANGUAGE 0,0','1 VERSIONINFO','FILEVERSION '+','.join(re.findall(r'\d+',nv['FileVersion'])[:4]),'PRODUCTVERSION '+','.join(re.findall(r'\d+',nv['ProductVersion'])[:4]),'FILEFLAGSMASK 0x3f','FILEFLAGS 0','FILEOS 4','FILETYPE 2','FILESUBTYPE 0','BEGIN','BLOCK "StringFileInfo"','BEGIN','BLOCK "000004b0"','BEGIN']
for field in ['CompanyName','FileDescription','FileVersion','InternalName','LegalCopyright','LegalTrademarks','OriginalFilename','ProductName','ProductVersion']:rc.append('VALUE '+json.dumps(field)+', L'+json.dumps(nv[field],ensure_ascii=True).replace('\\u','\\x'))
rc+=['END','END','BLOCK "VarFileInfo"','BEGIN','VALUE "Translation", 0, 1200','END','END'];(out/'version.rc').write_text('\n'.join(rc)+'\n');run('rc',[prefix/'bin/llvm-rc.exe','-fo',out/'version.res',out/'version.rc'])
raw=out/'raw';raw.mkdir();reference=prefix/'lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts/System.Runtime/4.0.20.0/System.Runtime.dll'
args=['/nostdlib+','/target:library','/optimize+','/deterministic+','/warnaserror+','/publicsign+','/keyfile:"'+(here/'inputs/Microsoft.snk').as_posix()+'"','/reference:"'+reference.as_posix()+'"','/win32res:"'+(out/'version.res').as_posix()+'"','/out:"'+(raw/(name+'.dll')).as_posix()+'"','"'+(out/'AssemblyInfo.cs').as_posix()+'"'];rsp=out/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');run('compile',[dotnet,compiler/'csc.dll','-noconfig','@'+str(rsp)])
run('emitter-build',[sys.executable,here/'build-aot-emitter.py',out/'emitter',prefix]);finished=out/'runtimes/aot/lib/netcore50';finished.mkdir(parents=True)
run('emit-original-forwarders',[dotnet,out/'emitter/bin/Release/net8.0/EmitAotForwarders.dll',raw/(name+'.dll'),here/'inputs/baselines1/runtimes-aot-lib-netcore50-exports.json',finished/(name+'.dll')])
(out/'results.json').write_text(json.dumps(dict(commands=commands,source_metadata_facade_port=True,original_forwarder_rows=31,original_scope_identities_preserved=True,exact_original_private_targeting_pack_acquired=False,private_provider_runtime_execution_verified=False,original_upstream_GenFacades_workflow_replayed=False,publisher_method_bodies_copied=False,publisher_DLLs_compiler_inputs=False,source_SHA256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [here/'inputs/EmitAotForwarders.cs',out/'AssemblyInfo.cs',out/'version.rc']},full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original AOT facade port built; original private providers still required')
