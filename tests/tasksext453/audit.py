"""Audit original Tasks.Extensions selections, exact source references and package layout."""
from pathlib import Path
import functools,hashlib,json,subprocess,sys,xml.etree.ElementTree as E,zipfile

root=Path(sys.argv[1]).resolve();here=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();record=json.loads((root/'results.json').read_text())
assert record['source_commit']=='637a8d58f72f2b0f1a71187530c3cf433e95a75a' and record['production_CSharp_changes']==0
for name,h in record['original_file_sha256'].items():assert sha(root/'source'/name)==h,name
assert E.parse(root/'source/src/System.Threading.Tasks.Extensions/dir.props').findtext('.//{*}AssemblyVersion')=='4.2.0.1'
assert E.parse(root/'source/src/System.Threading.Tasks.Extensions/pkg/System.Threading.Tasks.Extensions.pkgproj').findtext('.//{*}ExcludeReferenceAssets')=='true'
assert E.parse(root/'source/Packaging.props').findtext('.//{*}SkipValidatePackageTargetFramework')=='true'
assert E.parse(root/'archive/Archive.csproj').findtext('.//NoWarn')=='NU5128;NU5130'
assert set(record['profiles'])=={'lib/netstandard1.0','lib/netstandard2.0'} and all(c['exit_code']==0 for c in record['commands'])
native=functools.lru_cache(None)(lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip());posix=functools.lru_cache(None)(lambda p:Path(subprocess.check_output(['cygpath','-au',p],text=True).strip()).resolve())
matrix=json.loads((here/'inputs/source-contract-build-matrix.json').read_text());profiles={};unique=set()
for profile,item in record['profiles'].items():
 kind,tfm=profile.split('/');folder=root/kind/tfm;original=root/'source/src/System.Threading.Tasks.Extensions/src/System.Threading.Tasks.Extensions.csproj';project=E.parse(original);expected=set()
 for group in project.findall('{*}ItemGroup'):
  condition=group.get('Condition','')
  if condition=="'$(IsPartialFacadeAssembly)' == 'true'":continue
  if group.findall('{*}Compile'):assert condition in ['',"'$(IsPartialFacadeAssembly)' != 'true'"]
  expected.update((original.parent/e.get('Include').replace('$(CommonPath)','../../Common/src').replace('\\','/')).resolve() for e in group.findall('{*}Compile'))
 assert len(expected)==8;unique.update(expected)
 assert {str(p.relative_to(root/'source')):sha(p) for p in expected}==item['original_CSharp_inputs']
 assert {posix(p) for p in (folder/'Compile.txt').read_text().splitlines() if p}==expected|{folder/'Version.cs'}
 refs={posix(p) for p in (folder/'ReferencePath.txt').read_text().splitlines() if p};assert {native(p):sha(p) for p in refs}==item['reference_sha256']
 dep=item['source_dependency_inputs'];file=folder/'source-dependencies/System.Runtime.CompilerServices.Unsafe.dll';feed=Path('/clang64/lib/dotnet/library-packs')/dep['package'];assert sha(feed)==dep['package_sha256']
 with zipfile.ZipFile(feed) as z:assert file.read_bytes()==z.read(dep['asset'])
 assert sha(file)==dep['DLL_sha256']
 if tfm=='netstandard2.0':assert refs==set(Path('/clang64/lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll'))|{file} and len(refs)==114
 else:
  closure=set()
  def select(key):
   if key in closure:return
   closure.add(key)
   for reference in matrix[key]['references']:
    name,v=reference.split(', Version=');select(name+'/'+v.split(',')[0])
  for entry in project.findall('.//{*}Reference'):
   name=entry.get('Include')
   if name!='System.Runtime.CompilerServices.Unsafe':select(name+'/4.0.0.0')
  contract=Path('/clang64/lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts')
  assert refs=={contract/key/(key.split('/')[0]+'.dll') for key in closure}|{file}
  assert all('/4.0.0.0/' in str(p) for p in refs-{file})
 assert not (folder/'Analyzer.txt').read_text().strip();policy=(folder/'policy.txt').read_text().replace('\n',';').strip(';').split('|')
 assert policy[:2]==[tfm,'netstandard' if tfm=='netstandard2.0' else tfm] and policy[3:]==['1701;1702','7.3','true'] and 'DEBUG' not in policy[2]
 assert all(x in policy[2].split(';') for x in ['TRACE','RELEASE','netstandard'])
 assert sha(folder/'bin/Release/System.Threading.Tasks.Extensions.dll')==item['DLL_sha256'];profiles[profile]=dict(original_CSharp_inputs=8,exact_source_references=len(refs),DLL_sha256=item['DLL_sha256'],policy=policy)
provenance=json.loads((here/'inputs/published-provenance.json').read_text());package=root/'feed/System.Threading.Tasks.Extensions.4.5.3.nupkg'
def groups(md):return {g.get('targetFramework'):[{k:(v.removeprefix('[').removesuffix(', )') if k=='version' else v) for k,v in d.attrib.items()} for d in g] for g in md.findall('{*}dependencies/{*}group')}
with zipfile.ZipFile(package) as z:
 md=E.fromstring(z.read('System.Threading.Tasks.Extensions.nuspec')).find('{*}metadata');assert md.findtext('{*}id')=='System.Threading.Tasks.Extensions' and md.findtext('{*}version')=='4.5.3' and md.find('{*}repository').get('commit')==record['source_commit']
 assert groups(md)==groups(E.parse(here/'inputs/original.nuspec').find('{*}metadata'))
 members_by_path={__import__('urllib.parse',fromlist=['unquote']).unquote(n):n for n in z.namelist()};assert len(members_by_path)==len(z.namelist())
 assets={n for n in members_by_path if n.startswith(('lib/','ref/'))};assert assets==set(provenance['original_assets'])
 for name,h in provenance['original_assets'].items():
  if name.endswith('.dll'):
   profile=name.rsplit('/',1)[0];origin='lib/netstandard1.0' if 'portable-' in profile else profile;assert hashlib.sha256(z.read(members_by_path[name])).hexdigest()==record['profiles'][origin]['DLL_sha256']
  else:assert hashlib.sha256(z.read(members_by_path[name])).hexdigest()==h
 assert z.read(members_by_path['lib/portable-net45+win8+wp8+wpa81/System.Threading.Tasks.Extensions.dll'])==z.read('lib/netstandard1.0/System.Threading.Tasks.Extensions.dll')
 for name in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:assert z.read(name)==(root/'source'/name).read_bytes()
 assert z.read('version.txt')==(record['source_commit']+'\r\n').encode() and z.read('useSharedDesignerContext.txt')==(root/'source/pkg/useSharedDesignerContext.txt').read_bytes()
 members={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
report=dict(original_source_files_verified=len(record['original_file_sha256']),unique_original_CSharp_inputs=len(unique),production_CSharp_changes=0,profiles=profiles,all_original_compile_selections_exact=True,all_exact_source_reference_and_dependency_bytes_verified=True,portable_alias_byte_identical_to_NS10=True,compiler_warning_release_and_netstandard_policy_verified=True,original_reference_asset_exclusion_and_dependency_groups_preserved=True,all_original_DLL_XML_empty_marker_version_and_license_assets_preserved=True,original_documentation_text_imported_from_pinned_published_package=True,package_sha256=sha(package),archive_members=members,full_historical_runtime_matrix_verified=False,full_dependency_goal_complete=False)
(root/'producer-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
