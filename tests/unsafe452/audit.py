"""Audit unchanged source inputs, original profiles and all NuGet payload bytes."""
from pathlib import Path
import hashlib,json,subprocess,sys,xml.etree.ElementTree as E,zipfile
root=Path(sys.argv[1]).resolve();here=Path(__file__).parent
record=json.loads((root/'results.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert record['source_commit']=='02b11eeee1fbc5f3ef43a1452fe07efd25fa1715'
assert record['production_source_changes']==0
for name,digest in record['original_file_sha256'].items():assert sha(root/'source'/name)==digest,name
source=root/'source/src/System.Runtime.CompilerServices.Unsafe'
assert sha(source/'src/System.Runtime.CompilerServices.Unsafe.il')=='34b396807c45f676d770bfa28322d1dfeadd31fdfa149230ec135584fcf12fae'
assert sha(source/'ref/System.Runtime.CompilerServices.Unsafe.cs')=='6c65fb604520c1c4edd975ef1f765c9bbf3572940037950c2c0c679fe6abab45'
assert set(record['profiles'])=={'netstandard1.0','netstandard2.0','netcoreapp2.0'}
assert set(record['reference_profiles'])=={'netstandard1.0','netstandard2.0'}
assert all(c['exit_code']==0 for c in record['commands'])
for tfm,p in record['profiles'].items():
 assert sha(root/tfm/'System.Runtime.CompilerServices.Unsafe.dll')==p['DLL_sha256']
 assert sha(root/'source'/p['original_include_directory']/'coreassembly.h')==p['source_include_sha256']
 assert sha(root/tfm/'System.Runtime.CompilerServices.Unsafe.pdb')==p['PDB_sha256']
for tfm,p in record['reference_profiles'].items():
 assert sha(root/'ref'/tfm/'System.Runtime.CompilerServices.Unsafe.dll')==p['output_sha256']
 for cmd in record['commands']:
  if any('ref/'+tfm+'/compile.rsp' in a for a in cmd['command']):break
 else:raise AssertionError(tfm)
 rsp=(root/'ref'/tfm/'compile.rsp').read_text();assert '/warnaserror+' in rsp and '/unsafe+' in rsp and '/publicsign+' in rsp
 assert '/langversion:7.3' in rsp and '/win32res:' in rsp
 assert '/refonly' not in rsp
native=json.loads((here/'inputs/version-policy.json').read_text())['native_VERSIONINFO'];assert record['native_VERSIONINFO']==native
rc=(root/'native-resource/version.rc').read_text();assert 'L"Microsoft\\x00ae .NET Framework"' in rc and 'L"\\x00a9 Microsoft Corporation. All rights reserved."' in rc
package=root/'feed/System.Runtime.CompilerServices.Unsafe.4.5.2.nupkg'
provenance=json.loads((here/'inputs/published-provenance.json').read_text())
with zipfile.ZipFile(package) as z:
 md=E.fromstring(z.read('System.Runtime.CompilerServices.Unsafe.nuspec')).find('{*}metadata')
 assert md.findtext('{*}id')=='System.Runtime.CompilerServices.Unsafe' and md.findtext('{*}version')=='4.5.2'
 assert md.find('{*}repository').get('commit')==record['source_commit']
 groups={g.get('targetFramework'):{d.get('id'):d.get('version').removeprefix('[').removesuffix(', )') for d in g} for g in md.findall('{*}dependencies/{*}group')}
 # NuGet normalizes a bare lower-bound version to the interval [version, ).
 assert groups==provenance['original_dependency_groups'],groups
 expected={'lib/'+t+'/System.Runtime.CompilerServices.Unsafe.dll' for t in record['profiles']}|{'ref/'+t+'/System.Runtime.CompilerServices.Unsafe.dll' for t in record['reference_profiles']}
 assert {n for n in z.namelist() if n.endswith('.dll')}==expected
 for tfm in record['profiles']:
  assert z.read('lib/'+tfm+'/System.Runtime.CompilerServices.Unsafe.dll')==(root/tfm/'System.Runtime.CompilerServices.Unsafe.dll').read_bytes()
  assert z.read('lib/'+tfm+'/System.Runtime.CompilerServices.Unsafe.xml')==(source/'src/System.Runtime.CompilerServices.Unsafe.xml').read_bytes()
 for tfm in record['reference_profiles']:assert z.read('ref/'+tfm+'/System.Runtime.CompilerServices.Unsafe.dll')==(root/'ref'/tfm/'System.Runtime.CompilerServices.Unsafe.dll').read_bytes()
 for lic in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:assert z.read(lic)==(root/'source'/lic).read_bytes()
 members={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
report=dict(original_source_files_verified=len(record['original_file_sha256']),production_source_changes=0,all_original_runtime_and_reference_profiles_preserved=True,original_dependency_groups_preserved=True,original_XML_and_license_bytes_preserved=True,original_native_VERSIONINFO_preserved=True,original_IL_and_CSharp_source_hashes_verified=True,package_sha256=sha(package),archive_members=members,full_historical_runtime_matrix_verified=False,full_dependency_goal_complete=False)
(root/'producer-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
