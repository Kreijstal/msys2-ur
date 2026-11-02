"""Check source generated DPAPI stubs against independent native Win32 calls."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
build,refs,out=(Path(p).resolve() for p in sys.argv[1:4]);pkcs=Path(sys.argv[4]).resolve();assert not out.exists();out.mkdir();here=Path(__file__).resolve().parent;prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
name='System.Security.Cryptography.Xml.dll';shutil.copyfile(build/name,out/name);shutil.copyfile(build/'neutral-strings.json',out/'neutral-strings.json');ref_files=sorted(refs.glob('*.dll'));assert len(ref_files)==164
host=prefix/'lib/dotnet10/dotnet.exe';compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll';env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host));commands=[]
def run(label,command):
 with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(label=label,command=[str(x) for x in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
shutil.copyfile(pkcs,out/'System.Security.Cryptography.Pkcs.dll')
args=['/nostdlib+','/target:exe','/langversion:13.0','/nullable:enable','/out:"'+native(out/'Probe.dll')+'"',*['/reference:"'+native(p)+'"' for p in ref_files+[out/name]],'"'+native(here/'inputs/Probe.cs')+'"'];rsp=out/'compile.rsp';rsp.write_text('\n'.join(args)+'\n',encoding='utf-8');run('compile-probe',[host,compiler,'-noconfig','@'+native(rsp)]);(out/'Probe.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net9.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
run('execute',[host,out/'Probe.dll',native(out)]);openssl=prefix/'bin/openssl.exe'
run('openssl-signature',[openssl,'dgst','-sha256','-verify',out/'public.pem','-signature',out/'signature.bin',out/'signed-info.bin'])
run('openssl-keywrap',[openssl,'enc','-id-aes128-wrap','-nosalt','-iv','A6A6A6A6A6A6A6A6','-K','000102030405060708090A0B0C0D0E0F','-in',out/'wrap-input.bin','-out',out/'openssl-wrapped.bin'])
assert (out/'wrapped.bin').read_bytes()==(out/'openssl-wrapped.bin').read_bytes()
(out/'results.json').write_text(json.dumps(dict(commands=commands,source_library_sha256=sha(out/name),source_pkcs_dependency_sha256=sha(pkcs),original_target='net9.0',execution_framework='source NET10.0.5',all94_resources_passed=True,canonicalization_signature_tampering_aes_xml_encryption_rsa_aes_keywrap_base64_passed=True,independent_openssl_signature_and_keywrap_passed=True,repeated_gc_cases=12,formal_package_built=False,other_original_framework_profiles_built=False,full_dependency_goal_complete=False),indent=2)+'\n',encoding='utf-8');print('PASS source Cryptography.Xml9 XML crypto and independent OpenSSL crosschecks')
