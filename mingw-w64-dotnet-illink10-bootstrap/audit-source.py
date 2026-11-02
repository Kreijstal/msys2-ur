"""Verify every selected source byte and the exact Cecil VMR production inputs."""
from pathlib import Path
import hashlib
import json
import sys
import subprocess,tarfile

root, out = (Path(p).resolve() for p in sys.argv[1:])
here = Path(__file__).resolve().parent
record = json.loads((out / 'source-inputs.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
base_native=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
def posix(p):
 p=p.replace('\\','/').rstrip('/')
 if p.lower().startswith(base_native.lower()+'/'):return root/p[len(base_native)+1:]
 return Path(subprocess.check_output(['cygpath','-u',p],text=True).strip())
runtime_wanted={};cecil_wanted={}
counts = {}
for name, project in record['projects'].items():
    base = out / 'cecil-source' if name.startswith('Mono.Cecil') else root / 'r'
    assert project['production_cs_changes'] == 0
    for path, expected in project['original_cs'].items():
        assert sha(base / path) == expected, (name, path)
    for path, expected in project.get('resource_files_sha256', {}).items():
        assert sha(base / path) == expected, (name, path)
    actual={posix(p) for p in (out/name/'obj/Release/net8.0/Compile.txt').read_text().splitlines() if p}
    originals={base/p for p in project['original_cs']}
    assert {p for p in actual if p.is_relative_to(base)}==originals,(name,originals-actual)
    if name.startswith('Mono.Cecil'):cecil_wanted.update(project['original_cs'])
    else:runtime_wanted.update(project['original_cs']);runtime_wanted.update(project.get('resource_files_sha256',{}))
    product = out / name / 'bin/Release/net8.0' / (name + '.dll')
    assert product.is_file(), product
    deployed = out / 'illink/bin/Release/net8.0' / (name + '.dll')
    assert sha(deployed) == sha(product), (name, 'deployed tool bytes differ')
    counts[name] = len(project['original_cs'])
vmr = json.loads((here / 'inputs/cecil-vmr-source-audit.json').read_text())
assert vmr['vmr_commit'] == '12f41dd0da1a94621e039e27aef264179c1104b5'
assert vmr['cecil_source_commit'] == record['cecil_source_commit']
for path, expected in vmr['verified_original_inputs'].items():
    data = (out / 'cecil-source' / path).read_bytes()
    assert hashlib.sha256(data).hexdigest() == expected['sha256'], path
    assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == expected['git_blob_sha1'], path
assert (out / 'build.exit').read_text().strip() == '0'
assert 'IL Linker' in (out / 'help.log').read_text()
versions = json.loads((out / 'illink/bin/Release/net8.0/illink.deps.json.version-metadata.json').read_text())
for name in ['System.Collections.Immutable', 'System.Reflection.Metadata']:
    assets = [item for item in versions if item['asset'] == name + '.dll']
    assert assets and all(item['actual_assembly_version'] == '10.0.0.0' for item in assets)
for path,entry in vmr['verified_original_inputs'].items():cecil_wanted[path]=entry['sha256']
for path in ['eng/Version.Details.xml','eng/Versions.props','src/tools/illink/src/linker/Mono.Linker.csproj','src/tools/illink/src/ILLink.Shared/ILLink.Shared.projitems','src/tools/illink/Directory.Build.props','Directory.Build.props','src/libraries/Directory.Build.props']:
 runtime_wanted[path]=sha(root/'r'/path)
archive_counts={}
for name,path,wanted,commit in [('runtime',root/'runtime-v10.0.5.tar.gz',runtime_wanted,record['runtime_commit']),('cecil',root/'cecil-27abc572.tar.gz',cecil_wanted,record['cecil_source_commit'])]:
 verified=set()
 with tarfile.open(path) as t:
  assert t.pax_headers['comment']==commit
  for m in t:
   relative=m.name.partition('/')[2]
   if m.isfile() and relative in wanted:assert hashlib.sha256(t.extractfile(m).read()).hexdigest()==wanted[relative],relative;verified.add(relative)
 assert verified==set(wanted),(name,set(wanted)-verified)
 archive_counts[name]=len(verified)
for path,item in json.loads((out/'tool-inputs.json').read_text()).items():assert sha(posix(path))==item['sha256'],path
result = dict(all_original_sources_match=True,actual_original_compile_items_match=True,original_archive_inputs_verified=archive_counts, original_cs_by_project=counts,
              cecil_exact_vmr_inputs=len(vmr['verified_original_inputs']),
              removed_binary_inputs=len(record['removed_binary_inputs']),
              source_archive_sha256=record['cecil_source_archive_sha256'],
              private_bootstrap_framework='net8.0', full_sdk10_built=False,
              full_dependency_goal_complete=False)
(out / 'source-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print('PASS seven complete source projects, exact Cecil VMR inputs and original-source hashes:', counts)
