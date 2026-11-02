"""Verify installed JSON10 NET8 NuGets against exact source producer and analyzer assets."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile,zipfile
archive,prepared,output=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
names=['System.Text.Json','System.Text.Encodings.Web','System.IO.Pipelines']
expected={'clang64/lib/dotnet/library-packs/'+name.lower()+'.10.0.5.nupkg':prepared/'feed'/(name+'.10.0.5.nupkg') for name in names}
files={};process=subprocess.Popen(['zstd','-dc',str(archive)],stdout=subprocess.PIPE)
with tarfile.open(fileobj=process.stdout,mode='r|') as t:
 for m in t:
  if m.isdir() or m.name.startswith('.'):continue
  assert m.isfile() and (m.name in expected or m.name.startswith(('clang64/share/doc/dotnet-json10-net8/','clang64/share/licenses/dotnet-json10-net8/'))),m.name
  data=t.extractfile(m).read();assert (Path('/')/m.name).read_bytes()==data,m.name
  if m.name in expected:assert expected[m.name].read_bytes()==data,m.name
  files[m.name]=hashlib.sha256(data).hexdigest()
assert process.wait()==0
assert len(files)==13 and set(expected)<=set(files),len(files)
assets={};generator=Path('/clang64/lib/dotnet/generator-packs/runtime-10.0.5/analyzers/dotnet/cs')
for name in names:
 with zipfile.ZipFile(prepared/'feed'/(name+'.10.0.5.nupkg')) as z:
  for p in z.namelist():
   if p.startswith('lib/'):
    assert p.startswith('lib/net8.0/')
    assert z.read(p)==(prepared/name/'bin/Release/net8.0'/p.removeprefix('lib/net8.0/')).read_bytes(),p
    assets[name+':'+p]=hashlib.sha256(z.read(p)).hexdigest()
   elif p.startswith('analyzers/'):
    assert p.startswith('analyzers/dotnet/roslyn4.4/cs/')
    assert z.read(p)==(generator/p.removeprefix('analyzers/dotnet/roslyn4.4/cs/')).read_bytes(),p
    assets[name+':'+p]=hashlib.sha256(z.read(p)).hexdigest()
assert sum(p.endswith('.dll') for p in assets)==17
assert sum(p.endswith('.xml') for p in assets)==3
result=dict(formal_pacman_installed=True,installed_payload_files_verified=len(files),installed_nugets_verified=3,shipping_runtime_assemblies_verified=3,shipping_analyzer_and_satellite_assemblies_verified=14,shipping_xml_documentation_files_verified=3,package_archive_sha256=sha(archive),installed_files_sha256=files,all_shipping_assets_sha256=assets,complete_original_target_variants=False,source_illink_library_processing_verified=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(result,indent=2)+'\n');print('PASS 13 exact installed files, three NET8 runtime DLLs/XML docs and original JSON analyzer/13 satellites in three NuGets')
