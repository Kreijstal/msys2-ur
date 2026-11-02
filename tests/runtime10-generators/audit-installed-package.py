"""Verify every installed generator/satellite and the complete package payload."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile
archive,root,output=(Path(p).resolve() for p in sys.argv[1:])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
stage=root/'stage';manifest=json.loads((stage/'source-artifacts.json').read_text());prefix='clang64/lib/dotnet/generator-packs/runtime-10.0.5/'
expected={prefix+name:stage/name for name in [*manifest['files'],'source-artifacts.json']}
assert len(expected)==74 and sum(name.endswith('.dll') for name in expected)==71
files={};process=subprocess.Popen(['zstd','-dc',str(archive)],stdout=subprocess.PIPE)
with tarfile.open(fileobj=process.stdout,mode='r|') as t:
 for m in t:
  if m.isdir() or m.name.startswith('.'):continue
  assert m.isfile() and (m.name in expected or m.name.startswith(('clang64/share/doc/dotnet-runtime10-generators/','clang64/share/licenses/dotnet-runtime10-generators/'))),m.name
  data=t.extractfile(m).read();assert (Path('/')/m.name).read_bytes()==data,m.name
  if m.name in expected:assert data==expected[m.name].read_bytes(),m.name
  files[m.name]=hashlib.sha256(data).hexdigest()
assert process.wait()==0
assert len(files)==86 and set(expected)<=set(files),len(files)
for name,digest in manifest['files'].items():assert sha(stage/name)==digest,name
for name in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:
 assert (stage/name).read_bytes()==(root/'r'/name).read_bytes()
 assert (Path('/clang64/share/licenses/dotnet-runtime10-generators')/name).read_bytes()==(root/'r'/name).read_bytes()
assert Path('/clang64/share/licenses/dotnet-runtime10-generators/Arcade-LICENSE.TXT').read_bytes()==(root/'Arcade-LICENSE.TXT').read_bytes()
references=Path('/clang64/lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0')
reference_status=json.loads(Path('/clang64/share/doc/dotnet-reference10/build-status.json').read_text())
reference_inputs={p.name:sha(p) for p in references.glob('*.dll')};assert len(reference_inputs)==167
for name,digest in reference_inputs.items():assert reference_status['projects'][Path(name).stem]['output_sha256']==digest,name
result=dict(formal_pacman_installed=True,package_archive_sha256=sha(archive),installed_payload_files_verified=len(files),installed_primary_generator_assemblies_verified=6,installed_satellite_assemblies_verified=65,installed_files_sha256=files,no_roslyn_runtime_replacement_assets_shipped=True,json_runtime_test_fixture_shipped=False,installed_reference10_files_sha256=reference_inputs,full_targeting_pack_installed=False,full_framework10_built=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(result,indent=2)+'\n')
print('PASS 86 exact installed files: all six generators/65 satellites, manifest, source records and original licenses')
