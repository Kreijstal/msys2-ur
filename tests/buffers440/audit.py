"""Audit unchanged original selections, exact references, compiler policy and package."""
from pathlib import Path
import functools,hashlib,json,subprocess,sys,xml.etree.ElementTree as E,zipfile
root=Path(sys.argv[1]).resolve();here=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record=json.loads((root/'results.json').read_text());assert record['source_commit']=='8321c729934c0f8be754953439b88e6e1c120c24' and record['production_CSharp_changes']==0
for name,digest in record['original_file_sha256'].items():assert sha(root/'source'/name)==digest,name
assert E.parse(root/'source/src/System.Buffers/dir.props').findtext('.//{*}AssemblyVersion')=='4.0.2.0'
assert E.parse(root/'source/Packaging.props').findtext('.//{*}XmlDocPackageVersion')=='2.0.0-preview3-25511-0'
assert E.parse(root/'source/Packaging.props').findtext('.//{*}SkipValidatePackageTargetFramework')=='true'
assert E.parse(root/'archive/Archive.csproj').findtext('.//NoWarn')=='NU5128'
assert set(record['profiles'])=={'lib/netstandard1.1','lib/netstandard2.0','ref/netstandard1.1','ref/netstandard2.0'}
assert all(c['exit_code']==0 for c in record['commands'])
posix=functools.lru_cache(None)(lambda s:Path(subprocess.check_output(['cygpath','-au',s],text=True).strip()).resolve())
native=functools.lru_cache(None)(lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip())
profiles={};unique=set()
for profile,item in record['profiles'].items():
 kind,tfm=profile.split('/');folder=root/kind/tfm;original=root/'source/src/System.Buffers'/('src' if kind=='lib' else 'ref')/'System.Buffers.csproj';project=E.parse(original)
 expected={(original.parent/e.get('Include').replace('\\','/')).resolve() for e in project.findall('.//{*}Compile')}
 if kind=='lib':expected.add(root/'source/src/Common/src/System/SR.cs')
 assert len(expected)==(6 if kind=='lib' else 1);unique.update(expected)
 assert {str(p.relative_to(root/'source')):sha(p) for p in expected}==item['original_CSharp_inputs']
 actual={posix(s) for s in (folder/'Compile.txt').read_text().splitlines() if s};generated={folder/'Version.cs'}|({folder/'SR.Generated.cs'} if kind=='lib' else set());assert actual==expected|generated
 refs={posix(s) for s in (folder/'ReferencePath.txt').read_text().splitlines() if s};assert {native(p):sha(p) for p in refs}==item['reference_sha256']
 if tfm=='netstandard2.0':assert len(refs)==113
 else:
  matrix=json.loads((here/'inputs/source-contract-build-matrix.json').read_text());closure=set()
  def select(key):
   if key in closure:return
   assert key in matrix;closure.add(key)
   for reference in matrix[key]['references']:
    name,version=reference.split(', Version=');select(name+'/'+version.split(',')[0])
  roots={e.get('Include') for e in project.findall('.//{*}Reference')}
  assert len(roots)==(5 if kind=='lib' else 1)
  for name in roots:select(name+'/4.0.0.0')
  contracts=Path('/clang64/lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts')
  assert refs=={contracts/key/(key.split('/')[0]+'.dll') for key in closure}
  assert all('/4.0.0.0/' in str(p) for p in refs)
 assert not (folder/'Analyzer.txt').read_text().strip()
 policy=(folder/'policy.txt').read_text().replace('\n',';').strip(';').split('|');assert policy[:2]==[tfm,'netstandard' if tfm=='netstandard2.0' else tfm];assert policy[3:]==['1701;1702','7.3','true'],policy
 assert 'DEBUG' not in policy[2]
 assert sha(folder/'bin/Release/System.Buffers.dll')==item['DLL_sha256']
 tree=E.parse(folder/'Library.csproj');assert tree.findtext('.//AllowUnsafeBlocks')=='true' and tree.findtext('.//Optimize')=='true'
 profiles[profile]=dict(original_CSharp_inputs=len(expected),exact_source_references=len(refs),DLL_sha256=item['DLL_sha256'],policy=policy)
provenance=json.loads((here/'inputs/published-provenance.json').read_text());docs=json.loads((here/'inputs/documentation-provenance.json').read_text());package=root/'feed/System.Buffers.4.4.0.nupkg'
assert record['documentation']==docs
with zipfile.ZipFile(package) as z:
 md=E.fromstring(z.read('System.Buffers.nuspec')).find('{*}metadata');assert md.findtext('{*}id')=='System.Buffers' and md.findtext('{*}version')=='4.4.0';assert md.find('{*}repository').get('commit')==record['source_commit']
 groups={g.get('targetFramework'):[{k:(v.removeprefix('[').removesuffix(', )') if k=='version' else v) for k,v in d.attrib.items()} for d in g] for g in md.findall('{*}dependencies/{*}group')}
 assert groups==provenance['original_dependency_attributes'],groups
 assert {n for n in z.namelist() if n.endswith('.dll')}=={p+'/System.Buffers.dll' for p in record['profiles']}
 for profile,item in record['profiles'].items():
  assert hashlib.sha256(z.read(profile+'/System.Buffers.dll')).hexdigest()==item['DLL_sha256']
  name=profile+'/System.Buffers.xml';assert hashlib.sha256(z.read(name)).hexdigest()==docs['XML_asset_sha256'][name] and z.read(name)==(here/'inputs/System.Buffers.xml').read_bytes()
 for kind in ['lib','ref']:assert z.read(kind+'/netcoreapp2.0/_._')==b''
 assert z.read('version.txt')==(record['source_commit']+'\r\n').encode();assert z.read('useSharedDesignerContext.txt')==(root/'source/pkg/useSharedDesignerContext.txt').read_bytes()==b''
 for lic in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:assert z.read(lic)==(root/'source'/lic).read_bytes()
 members={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
report=dict(original_source_files_verified=len(record['original_file_sha256']),unique_original_CSharp_inputs=len(unique),production_CSharp_changes=0,profiles=profiles,all_original_compile_selections_exact=True,all_exact_source_reference_bytes_verified=True,compiler_warning_and_release_policy_verified=True,original_dependency_groups_and_Compile_exclusions_preserved=True,all_original_DLL_XML_framework_marker_version_and_license_assets_preserved=True,original_private_Intellisense_package_reacquired=False,original_documentation_text_imported_from_pinned_published_package=True,package_sha256=sha(package),archive_members=members,full_historical_runtime_matrix_verified=False,full_dependency_goal_complete=False)
(root/'producer-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
