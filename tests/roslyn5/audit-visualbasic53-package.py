"""Independently inspect actual VB/server companion archive and CSharp isolation."""
from pathlib import Path
import hashlib,json,subprocess,sys
root=Path(sys.argv[1]).resolve();release=sys.argv[2] if len(sys.argv)==3 else '1';assert release in {'1','2'}
packages=list(root.glob('*-5.3.0.2.26113.113-'+release+'-any.pkg.tar.zst'));assert len(packages)==1
package=packages[0];read=lambda name:subprocess.check_output(['/usr/bin/bsdtar','-xOf',str(package),name]);names=subprocess.check_output(['/usr/bin/bsdtar','-tf',str(package)],text=True).splitlines();payload={}
assert 'pkgname = mingw-w64-clang-x86_64-dotnet-visualbasic53-bootstrap\n' in read('.PKGINFO').decode()
for name in names:
 if name.startswith('.') or name.endswith('/'):continue
 assert name.startswith('clang64/'),name
 data=read(name);assert data==(root/'src/package-prefix'/name[len('clang64/'):]).read_bytes(),name
 payload[name]=hashlib.sha256(data).hexdigest()
doc='clang64/share/doc/dotnet-visualbasic53-bootstrap/';manifest=json.loads(read(doc+'payload-files.json'))
assert {'clang64/'+name:d for name,d in manifest.items()}=={name:d for name,d in payload.items() if name!=doc+'payload-files.json'}
tool='clang64/lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/'
dlls=[name for name in payload if name.startswith(tool) and name.endswith('.dll')]
assert len(dlls)==16 and sum(name.endswith('.resources.dll') for name in dlls)==13
assert payload[tool+'Microsoft.CodeAnalysis.VisualBasic.dll']==json.loads(read(doc+'vb-build-results.json'))['output_sha256']
for name,record in json.loads(read(doc+'clients-build-results.json'))['projects'].items():assert payload[tool+name+'.dll']==record['output_sha256']
for name,d in json.loads(read(doc+'localization-results.json'))['satellite_files_sha256'].items():assert payload[tool+name]==d
csharp=json.loads(Path('/clang64/share/doc/dotnet-csharp-compiler53-bootstrap/payload-files.json').read_text())
assert not set(manifest)&set(csharp)
limits=json.loads(read(doc+'package-limits.json'));assert not limits['full_sdk10_built'] and not limits['full_dependency_goal_complete']
report=dict(package=package.name,sha256=hashlib.sha256(package.read_bytes()).hexdigest(),regular_payload_files=len(payload),files_sha256=payload,provided_primary_compiler_dlls=3,source_satellites=13,all_actual_package_and_staged_bytes_match=True,csharp_dependency_files_not_overwritten=True,full_sdk10_built=False,full_dependency_goal_complete=False)
(root/'artifact-audit.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS actual VB/server archive:',len(payload),'payload files,3 primary DLLs,13 satellites,disjoint CSharp ownership')
