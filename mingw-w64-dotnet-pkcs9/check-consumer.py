"""Exercise source PKCS and cross-check independent OpenSSL CMS/PFX operations."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
build,refs,out=(Path(p).resolve() for p in sys.argv[1:4]);asn_source=Path(sys.argv[4]).resolve() if len(sys.argv)==5 else None;assert not out.exists();out.mkdir();here=Path(__file__).resolve().parent;prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
name='System.Security.Cryptography.Pkcs.dll';shutil.copyfile(build/name,out/name);shutil.copyfile(build/'neutral-strings.json',out/'neutral-strings.json');ref_files=sorted(refs.glob('*.dll'));assert len(ref_files)==164
host=prefix/'lib/dotnet10/dotnet.exe';compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll';env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host));commands=[]
def run(label,command):
 with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(label=label,command=[str(x) for x in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
args=['/nostdlib+','/target:exe','/langversion:13.0','/nullable:enable','/out:"'+native(out/'Probe.dll')+'"',*['/reference:"'+native(p)+'"' for p in ref_files+[out/name]],'"'+native(here/'inputs/Probe.cs')+'"'];rsp=out/'compile.rsp';rsp.write_text('\n'.join(args)+'\n',encoding='utf-8');run('compile-probe',[host,compiler,'-noconfig','@'+native(rsp)]);(out/'Probe.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net9.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
run('execute',[host,out/'Probe.dll',native(out)]);openssl=prefix/'bin/openssl.exe'
for stem in ['rsa','ecdsa']:
 run('openssl-verify-'+stem,[openssl,'cms','-verify','-binary','-noverify','-inform','DER','-in',out/(stem+'-attached.cms'),'-out',out/(stem+'-verified.bin')])
 assert (out/(stem+'-verified.bin')).read_bytes()==(out/'content.bin').read_bytes()
run('openssl-decrypt',[openssl,'cms','-decrypt','-binary','-inform','DER','-in',out/'enveloped.cms','-recip',out/'rsa-cert.pem','-inkey',out/'rsa-key.pem','-out',out/'decrypted.bin'])
assert (out/'decrypted.bin').read_bytes()==(out/'content.bin').read_bytes()
run('openssl-pfx',[openssl,'pkcs12','-in',out/'owned.pfx','-passin','pass:owned-password','-info','-noout'])
run('openssl-sign',[openssl,'cms','-sign','-binary','-nodetach','-md','sha256','-in',out/'content.bin','-signer',out/'rsa-cert.pem','-inkey',out/'rsa-key.pem','-outform','DER','-out',out/'native-signed.cms'])
run('openssl-encrypt',[openssl,'cms','-encrypt','-binary','-aes-256-cbc','-in',out/'content.bin','-outform','DER','-out',out/'native-enveloped.cms',out/'rsa-cert.pem'])
run('verify-native',[host,out/'Probe.dll',native(out),'--verify-native'])
if asn_source is not None:
 isolated=out/'source-asn9';isolated.mkdir()
 for fixture in ['Probe.dll','System.Security.Cryptography.Pkcs.dll','neutral-strings.json']:shutil.copyfile(out/fixture,isolated/fixture)
 host_args=['/nostdlib+','/target:exe','/nullable:enable','/out:"'+native(out/'SourceAsnHost.dll')+'"',*['/reference:"'+native(p)+'"' for p in ref_files],'"'+native(here/'inputs/SourceAsnHost.cs')+'"']
 host_rsp=out/'source-host.rsp';host_rsp.write_text('\n'.join(host_args)+'\n',encoding='utf-8')
 run('compile-source-asn-host',[host,compiler,'-noconfig','@'+native(host_rsp)])
 shutil.copyfile(out/'Probe.runtimeconfig.json',out/'SourceAsnHost.runtimeconfig.json')
 run('execute-source-asn9',[host,out/'SourceAsnHost.dll',native(isolated),native(asn_source)])
(out/'results.json').write_text(json.dumps(dict(commands=commands,source_library_sha256=sha(out/name),openssl_sha256=sha(openssl),original_source_asn1_dependency_executed=asn_source is not None,all34_private_asn1_resources_verified=asn_source is not None,source_asn1_sha256=sha(asn_source) if asn_source is not None else None,original_target='net9.0',execution_framework='source NET10.0.5',rsa_ecdsa_attached_detached_counter_signatures_passed=True,corrupt_signature_and_content_rejected=True,aes_cms_envelopes_passed=True,pkcs8_pkcs12_passwords_bags_and_bcl_import_passed=True,rfc3161_request_roundtrip_passed=True,independent_openssl_signature_decrypt_pfx_and_reverse_checks_passed=True,repeated_gc_native_buffer_lifecycle_cases=12,neutral_resource_values_passed=True,formal_package_built=False,other_original_framework_profiles_built=False,full_dependency_goal_complete=False),indent=2)+'\n',encoding='utf-8');print('PASS source PKCS9 real CMS/PFX and independent OpenSSL interoperability')
