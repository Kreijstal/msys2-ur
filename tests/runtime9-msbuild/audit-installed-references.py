"""Compare every installed public contract and package file with its source output."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile,xml.etree.ElementTree as E
archive,prepared,output=(Path(p).resolve() for p in sys.argv[1:])
refs=prepared/'ref/net9.0'
expected={'clang64/lib/dotnet/reference-packs/runtime-9.0.11/ref/net9.0/'+p.name:p for p in refs.glob('*.dll')}
assert len(expected)==164
files={};process=subprocess.Popen(['zstd','-dc',str(archive)],stdout=subprocess.PIPE)
with tarfile.open(fileobj=process.stdout,mode='r|') as t:
 for m in t:
  if m.isdir() or m.name.startswith('.'):continue
  assert m.isfile() and (m.name in expected or m.name.startswith(('clang64/share/doc/dotnet-reference9-servicing/','clang64/share/licenses/dotnet-reference9-servicing/'))),m.name
  data=t.extractfile(m).read();assert (Path('/')/m.name).read_bytes()==data,m.name
  if m.name in expected:assert data==expected[m.name].read_bytes(),m.name
  files[m.name]=hashlib.sha256(data).hexdigest()
assert process.wait()==0
assert len(files)==175 and set(expected)<=set(files),len(files)
arcade=prepared.parent/'arcade-runtime9-6666973b.tar.gz'
assert hashlib.sha256(arcade.read_bytes()).hexdigest()=='6305eac8a59c6cc9675f82afaac365f8519d8cb8e55bec6a98c9eeb6951b4a2c'
with tarfile.open(arcade) as t:
 member=next(m for m in t if m.name.endswith('/tools/StrongName.props'))
 policy=E.fromstring(t.extractfile(member).read())
keys=list((prepared/'keys').glob('*.pubkey'));assert len(keys)==5
for key in keys:assert key.read_bytes()==bytes.fromhex(policy.findtext('.//'+key.stem+'PublicKey')),key
result=dict(package_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),installed_payload_files_verified=len(files),installed_public_reference_assemblies_verified=164,private_facade_stubs_shipped=False,original_arcade_key_policies_verified=len(keys),installed_files_sha256=files,full_targeting_pack_installed=False,full_framework9_built=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(result,indent=2)+'\n')
print('PASS all 175 installed payload files and 164 exact source reference assemblies; no private facade stubs shipped')
