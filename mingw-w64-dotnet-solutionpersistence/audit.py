"""Verify real selected sources/resources against the pinned original archive."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile,zipfile
archive,prepared=(Path(p).resolve() for p in sys.argv[1:3]);source=Path(json.loads((prepared/'source-inputs.json').read_text())['source_root'].replace('E:/','/e/'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected={};actual={}
for kind in ['Compile','ReferencePath','Analyzer','EmbeddedResource']:
 for value in (prepared/'capture'/(kind+'.txt')).read_text(encoding='utf-8-sig').splitlines():
  if not value.strip():continue
  p=Path(subprocess.check_output(['cygpath','-u',value.strip()],text=True).strip());actual[str(p)]=sha(p)
  if p.is_relative_to(source) and not any(n in p.relative_to(source).parts for n in ['obj','bin']):expected[p.relative_to(source).as_posix()]=sha(p)
seen=set()
with tarfile.open(archive) as tar:
 for m in tar:
  n=m.name.split('/',1)[-1]
  if m.isfile() and n in expected:assert hashlib.sha256(tar.extractfile(m).read()).hexdigest()==expected[n],n;seen.add(n)
assert seen==set(expected)
assert any(n.endswith('src/AssemblyInfo.cs') for n in seen)
assert any(n.endswith('Errors.Designer.cs') for n in seen) and any(n.endswith('Errors.resx') for n in seen)
package=prepared/'feed/Microsoft.VisualStudio.SolutionPersistence.1.0.52.nupkg'
with zipfile.ZipFile(package) as z:
 dlls=[n for n in z.namelist() if n.endswith('.dll')];assert dlls==['lib/net8.0/Microsoft.VisualStudio.SolutionPersistence.dll'],dlls
record=dict(original_archive_inputs_verified=len(seen),original_inputs_sha256=expected,actual_compiler_reference_analyzer_and_resource_inputs_sha256=actual,source_package_sha256=sha(package),original_production_source_changes=0,original_target='net8.0',full_original_net472_profile_built=False,full_msbuild_built=False,full_sdk10_built=False,full_dependency_goal_complete=False)
(prepared/'source-audit.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS',len(seen),'original archive inputs;',len(actual),'actual compile/ref/resource inputs')
