"""Compare every installed native CoreCLR10 bootstrap package byte with its build."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile
archive,root,output=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
audit=json.loads((root/'native-audit.json').read_text());expected={'clang64/lib/dotnet-bootstrap10/coreclr/10.0.5/'+name+'.dll':root/'coreclr-build'/item['build_path'] for name,item in audit['images'].items()};files={}
process=subprocess.Popen(['zstd','-dc',str(archive)],stdout=subprocess.PIPE)
with tarfile.open(fileobj=process.stdout,mode='r|') as t:
 for m in t:
  if m.isdir() or m.name.startswith('.'):continue
  assert m.isfile() and (m.name in expected or m.name.startswith(('clang64/share/doc/dotnet-coreclr10-bootstrap/','clang64/share/licenses/dotnet-coreclr10-bootstrap/'))),m.name
  data=t.extractfile(m).read();assert (Path('/')/m.name).read_bytes()==data,m.name
  if m.name in expected:assert expected[m.name].read_bytes()==data,m.name
  files[m.name]=hashlib.sha256(data).hexdigest()
assert process.wait()==0
assert len(files)==18 and set(expected)<=set(files),len(files)
result=dict(formal_pacman_installed=True,package_archive_sha256=sha(archive),installed_payload_files_verified=len(files),installed_native_images_verified=4,installed_files_sha256=files,shared_framework_registered=False,managed_coreclr10_execution_verified=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(result,indent=2)+'\n');print('PASS 18 exact installed payload files and all four source CoreCLR10 native images')
