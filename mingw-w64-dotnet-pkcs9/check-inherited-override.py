"""Compile against the original reference, then exercise the source override."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys

root,out=(Path(p).resolve() for p in sys.argv[1:3]);out.mkdir()
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip())
host=prefix/'lib/dotnet10/dotnet.exe';refs=prefix/'lib/dotnet/reference-packs/runtime-9.0.11/ref/net9.0'
native=lambda p:Path(p).resolve().as_posix()
source=out/'Probe.cs';source.write_text('''using System;using System.Linq;using System.Security.Cryptography.Pkcs;
class Probe {static int Main(){try {var value=new Pkcs9LocalKeyId(new byte[]{1,2,3});if(!value.KeyId.Span.SequenceEqual(new byte[]{1,2,3}))throw new Exception("Initial cached key ID");Pkcs9AttributeObject contract=value;contract.CopyFrom(new Pkcs9LocalKeyId(new byte[]{9,8,7,6}));if(!value.KeyId.Span.SequenceEqual(new byte[]{9,8,7,6}))throw new Exception("Inherited contract failed to dispatch to cache-invalidating override");Console.WriteLine("PASS original reference-compiled inherited CopyFrom dispatches to unchanged source override and invalidates cached key ID");return 0;}catch(Exception error){Console.Error.WriteLine(error);return 1;}}}''')
contract=Path(sys.argv[3]).resolve() if len(sys.argv)==4 else root/'api-windows-release/System.Security.Cryptography.Pkcs.dll'
rsp=out/'compile.rsp';rsp.write_text('\n'.join(['/nostdlib+','/target:exe','/out:"'+native(out/'Probe.dll')+'"',*['/reference:"'+native(p)+'"' for p in list(refs.glob('*.dll'))+[contract]],'"'+native(source)+'"'])+'\n')
commands=[]
def run(label,command):
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
    commands.append(dict(label=label,command=[str(x) for x in command],exit_code=result.returncode))
    assert result.returncode==0,(label,result.returncode)
run('compile-original-reference',[host,prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll','-noconfig','@'+native(rsp)])
for profile in ['windows-release','generic-release']:
    folder=out/profile;folder.mkdir();shutil.copyfile(out/'Probe.dll',folder/'Probe.dll')
    shutil.copyfile(root/profile/'System.Security.Cryptography.Pkcs.dll',folder/'System.Security.Cryptography.Pkcs.dll')
    (folder/'Probe.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net9.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
    run(profile,[host,folder/'Probe.dll'])
(out/'results.json').write_text(json.dumps(dict(commands=commands,compiled_against_original_contract_sha256=hashlib.sha256(contract.read_bytes()).hexdigest(),both_original_profiles_inherited_dispatch_and_cache_invalidation_passed=True,raw_extra_override_retained=True,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original-reference inherited override dispatch and cache invalidation for both PKCS profiles')
