"""Independently compare package archive payloads to the checked source outputs."""
from pathlib import Path
import hashlib,io,json,subprocess,sys,xml.etree.ElementTree as E,zipfile

root=Path(sys.argv[1]).resolve();packages=list(root.glob('*.pkg.tar.zst'))
assert len(packages)==1,packages
package=packages[0];sha=lambda data:hashlib.sha256(data).hexdigest()
run=lambda *args:subprocess.check_output(['/usr/bin/bsdtar',*args])
entries=run('-tf',str(package)).decode().splitlines();files={}
for entry in entries:
 if entry.endswith('/') or entry.startswith('.'):continue
 data=run('-xOf',str(package),entry);expected=root/'pkg/mingw-w64-clang-x86_64-dotnet-maintenance-netstandard10'/entry
 assert expected.is_file() and data==expected.read_bytes(),entry
 files[entry]=sha(data)
nugets={name:data for name in files if name.endswith('.nupkg') for data in [run('-xOf',str(package),name)]}
expected={'system.memory.4.6.3.nupkg':('System.Memory','4.6.3'),
 'system.runtime.compilerservices.unsafe.6.1.2.nupkg':('System.Runtime.CompilerServices.Unsafe','6.1.2'),
 'system.threading.tasks.extensions.4.6.3.nupkg':('System.Threading.Tasks.Extensions','4.6.3')}
assert {Path(p).name for p in nugets}==set(expected)
for path,data in nugets.items():
 name,version=expected[Path(path).name]
 assert data==(root/'src/prepared/feed'/(name+'.'+version+'.nupkg')).read_bytes()
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  spec=E.fromstring(z.read(next(n for n in z.namelist() if n.endswith('.nuspec'))))
  repository=next(e for e in spec.iter() if e.tag.endswith('repository'))
  assert repository.get('commit')=='f62ca0009b038cab4725a720f386623a969d73ad'
  assert z.read('lib/netstandard2.0/'+name+'.dll')
  assert z.read('LICENSE') and z.read('lib/netstandard2.0/'+name+'.xml')
record=dict(package=package.name,package_sha256=sha(package.read_bytes()),regular_payload_files=len(files),
 files_sha256=files,three_updated_source_nugets_verified=True,original_buffer_vector_archives_not_shipped=True,
 full_dependency_goal_complete=False)
(root/'artifact-audit.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS independent archive audit:',len(files),'payload files; exactly three pinned-source NuGet updates')
