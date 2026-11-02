"""Independently audit the actual runtime package and its complete source closure."""
from pathlib import Path
import hashlib,json,subprocess,sys

root=Path(sys.argv[1]).resolve();packages=list(root.glob('*-10.0.5-1-any.pkg.tar.zst'))
assert len(packages)==1,packages
package=packages[0]
read=lambda name:subprocess.check_output(['/usr/bin/bsdtar','-xOf',str(package),name])
entries=subprocess.check_output(['/usr/bin/bsdtar','-tf',str(package)],text=True).splitlines()
assert 'pkgver = 10.0.5-1\n' in read('.PKGINFO').decode()
prefix='clang64/';payload={}
for name in entries:
 if name.startswith('.') or name.endswith('/'):continue
 assert name.startswith(prefix),name
 data=read(name)
 source=root/'src/package-prefix'/name.removeprefix(prefix)
 assert source.is_file() and data==source.read_bytes(),name
 payload[name]=hashlib.sha256(data).hexdigest()
doc=prefix+'share/doc/dotnet-runtime10-bootstrap/'
manifest=json.loads(read(doc+'payload-files.json'))
assert {prefix+name:digest for name,digest in manifest.items()}=={
 name:digest for name,digest in payload.items() if name!=doc+'payload-files.json'}
status=json.loads((root/'src/build-plan/build-status.json').read_text())
assert len(status)==190
expected={name+'.dll' for name,record in status.items() if record['kind']!='stub'}|{'System.Private.CoreLib.dll'}
assert len(expected)==172
native={'coreclr.dll','clrjit.dll','mscorrc.dll','clretwrc.dll',
 'hostpolicy.dll','System.IO.Compression.Native.dll','System.Globalization.Native.dll'}
framework=prefix+'lib/dotnet10/shared/Microsoft.NETCore.App/10.0.5/'
actual={name.removeprefix(framework) for name in payload if name.startswith(framework) and name.endswith('.dll')}
assert actual==expected|native,(sorted(actual-expected-native),sorted((expected|native)-actual))
for name,record in status.items():
 if record['kind']!='stub':assert payload[framework+name+'.dll']==record['output_sha256'],name
source_manifest=json.loads(read(prefix+'lib/dotnet10/source-payload.json'))
for name,record in source_manifest['source_files'].items():
 assert payload[prefix+'lib/dotnet10/'+name]==record['sha256'],name
limits=json.loads(read(doc+'package-limits.json'))
assert limits['managed_framework_assemblies']==172 and limits['private_seed_assemblies_shipped']==0
assert not limits['full_dependency_goal_complete'] and not limits['full_sdk10_built']
for name in ['compiler-source-audit.json','linked-results.json','runtime-results.json','host-results.json','asn-results.json','contract-results.json']:
 assert read(doc+name)
report=dict(package=package.name,sha256=hashlib.sha256(package.read_bytes()).hexdigest(),
 regular_payload_files=len(payload),files_sha256=payload,managed_assemblies=172,
 native_framework_dlls=7,private_seed_assemblies_shipped=0,
 all_original_build_outputs_and_source_component_bytes_verified=True,
 strict_contract_parity_verified=limits['strict_reference_api_shape_parity_verified'],
 full_runtime_compatibility_verified=False,full_sdk10_built=False,
 powershell76_built=False,full_dependency_goal_complete=False)
(root/'artifact-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS actual runtime package:172 managed assemblies,7 native framework DLLs, exact source component bytes and complete payload manifest')
