"""Independently inspect the actual pacman archive and every payload byte."""
from pathlib import Path
import hashlib,json,subprocess,sys
root=Path(sys.argv[1]).resolve();release=sys.argv[2] if len(sys.argv)==3 else '1'
assert release in {'1','2','3'}
packages=list(root.glob('*-5.3.0.2.26113.113-'+release+'-any.pkg.tar.zst'));assert len(packages)==1
package=packages[0];read=lambda n:subprocess.check_output(['/usr/bin/bsdtar','-xOf',str(package),n])
entries=subprocess.check_output(['/usr/bin/bsdtar','-tf',str(package)],text=True).splitlines();payload={}
assert 'pkgname = mingw-w64-clang-x86_64-dotnet-csharp-compiler53-bootstrap\n' in read('.PKGINFO').decode()
for n in entries:
 if n.startswith('.') or n.endswith('/'):continue
 assert n.startswith('clang64/'),n
 data=read(n);assert data==(root/'src/package-prefix'/n[len('clang64/'):]).read_bytes(),n
 payload[n]=hashlib.sha256(data).hexdigest()
doc='clang64/share/doc/dotnet-csharp-compiler53-bootstrap/'
manifest=json.loads(read(doc+'payload-files.json'))
assert {'clang64/'+n:d for n,d in manifest.items()}=={n:d for n,d in payload.items() if n!=doc+'payload-files.json'}
tool='clang64/lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/'
dlls=[n for n in payload if n.startswith(tool) and n.endswith('.dll')]
assert len(dlls)==29
assert sum(n.endswith('.resources.dll') for n in dlls)==26
status=json.loads(read(doc+'build-status.json'))
for name,r in status.items():assert payload[tool+name+'.dll']==r['output_sha256'],name
limits=json.loads(read(doc+'package-limits.json'))
assert not limits['visualbasic_and_compiler_server_built'] and not limits['full_sdk10_built'] and not limits['full_dependency_goal_complete']
record=dict(package=package.name,sha256=hashlib.sha256(package.read_bytes()).hexdigest(),regular_payload_files=len(payload),files_sha256=payload,source_compiler_dlls=3,source_satellites=26,all_actual_package_and_staged_bytes_match=True,full_sdk10_built=False,full_dependency_goal_complete=False)
(root/'artifact-audit.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS actual compiler archive:',len(payload),'payload files,3 compiler DLLs,26 satellites,all byte hashes match')
