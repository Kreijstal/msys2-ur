"""Compare every installed public contract and package file with its source output."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile,xml.etree.ElementTree as E
archive,prepared,output=(Path(p).resolve() for p in sys.argv[1:])
refs=prepared/'ref/net10.0'
expected={'clang64/lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0/'+p.name:p for p in refs.glob('*.dll')}
assert len(expected)==167
files={};process=subprocess.Popen(['zstd','-dc',str(archive)],stdout=subprocess.PIPE)
with tarfile.open(fileobj=process.stdout,mode='r|') as t:
 for m in t:
  if m.isdir() or m.name.startswith('.'):continue
  assert m.isfile() and (m.name in expected or m.name.startswith(('clang64/share/doc/dotnet-reference10/','clang64/share/licenses/dotnet-reference10/'))),m.name
  data=t.extractfile(m).read();assert (Path('/')/m.name).read_bytes()==data,m.name
  if m.name in expected:assert data==expected[m.name].read_bytes(),m.name
  files[m.name]=hashlib.sha256(data).hexdigest()
assert process.wait()==0
assert len(files)==178 and set(expected)<=set(files),len(files)
arcade=prepared.parent/'arcade-runtime10-4bf37ce6.tar.gz'
assert hashlib.sha256(arcade.read_bytes()).hexdigest()=='82f5f6dd63c0dcf3c0fc49b282207db5d889d9cc0939589d43b16c7fcfdf7d66'
with tarfile.open(arcade) as t:
 member=next(m for m in t if m.name.endswith('/tools/StrongName.props'))
 policy=E.fromstring(t.extractfile(member).read())
keys=list((prepared/'keys').glob('*.pubkey'));assert len(keys)==5
for key in keys:assert key.read_bytes()==bytes.fromhex(policy.findtext('.//'+key.stem+'PublicKey')),key
result=dict(package_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),installed_payload_files_verified=len(files),installed_public_reference_assemblies_verified=167,private_facade_stubs_shipped=False,original_arcade_key_policies_verified=len(keys),installed_files_sha256=files,full_targeting_pack_installed=False,full_framework10_built=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(result,indent=2)+'\n')
print('PASS all 178 installed payload files and 167 exact source reference assemblies; no private facade stubs shipped')
