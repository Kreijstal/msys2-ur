"""Audit original Memory selections, exact source references and package layout."""
from pathlib import Path
import functools,hashlib,json,runpy,subprocess,sys,xml.etree.ElementTree as E,zipfile

root=Path(sys.argv[1]).resolve();here=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();record=json.loads((root/'results.json').read_text())
assert record['source_commit']=='c6cf790234e063b855fcdb50f3fb1b3cfac73275' and record['production_CSharp_changes']==0
for name,h in record['original_file_sha256'].items():assert sha(root/'source'/name)==h,name
assert E.parse(root/'source/src/System.Memory/dir.props').findtext('.//{*}AssemblyVersion')=='4.0.1.1'
assert E.parse(root/'source/src/System.Memory/pkg/System.Memory.pkgproj').findtext('.//{*}ExcludeReferenceAssets')=='true'
assert E.parse(root/'source/src/System.Memory/src/System.Memory.csproj').findtext('.//{*}ILLinkClearInitLocals')=='true'
assert E.parse(root/'source/Packaging.props').findtext('.//{*}SkipValidatePackageTargetFramework')=='true'
assert E.parse(root/'archive/Archive.csproj').findtext('.//NoWarn')=='NU5128'
assert set(record['profiles'])=={'lib/netstandard1.1','lib/netstandard2.0'} and all(c['exit_code']==0 for c in record['commands'])
native=functools.lru_cache(None)(lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip());posix=functools.lru_cache(None)(lambda p:Path(subprocess.check_output(['cygpath','-au',p],text=True).strip()).resolve())
matrix=json.loads((here/'inputs/source-contract-build-matrix.json').read_text());profiles={};unique=set();private=None
for profile,item in record['profiles'].items():
 kind,tfm=profile.split('/');folder=root/kind/tfm;original=root/'source/src/System.Memory/src/System.Memory.csproj';project=E.parse(original);expected={root/'source/src/Common/src/System/SR.cs'}
 for group in project.findall('{*}ItemGroup'):
  condition=group.get('Condition','')
  if condition=="'$(IsPartialFacadeAssembly)' == 'true'":continue
  if group.findall('{*}Compile'):assert condition in ['',"'$(IsPartialFacadeAssembly)' != 'true'"]
  expected.update((original.parent/e.get('Include').replace('$(CommonPath)','../../Common/src').replace('\\','/')).resolve() for e in group.findall('{*}Compile'))
 assert len(expected)==102;unique.update(expected)
 assert {str(p.relative_to(root/'source')):sha(p) for p in expected}==item['original_CSharp_inputs']
 assert {posix(p) for p in (folder/'Compile.txt').read_text().splitlines() if p}==expected|{folder/'Version.cs',folder/'SR.Generated.cs'}
 refs={posix(p) for p in (folder/'ReferencePath.txt').read_text().splitlines() if p};assert {native(p):sha(p) for p in refs}==item['reference_sha256']
 dependencies=set()
 for name,dep in item['source_dependency_inputs'].items():
  file=folder/'source-dependencies'/name/(name+'.dll');dependencies.add(file);feed=Path('/clang64/lib/dotnet/library-packs')/dep['package'];assert sha(feed)==dep['package_sha256']
  with zipfile.ZipFile(feed) as z:assert file.read_bytes()==z.read(dep['asset'])
  assert sha(file)==dep['DLL_sha256']
 if tfm=='netstandard2.0':
  assert refs==set(Path('/clang64/lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll'))|dependencies and len(refs)==116
  assert set(item['source_dependency_inputs'])=={'System.Buffers','System.Runtime.CompilerServices.Unsafe','System.Numerics.Vectors'}
 else:
  assert set(item['source_dependency_inputs'])=={'System.Buffers','System.Runtime.CompilerServices.Unsafe'}
  closure=set()
  def select(key):
   if key in closure:return
   closure.add(key)
   for reference in matrix[key]['references']:
    name,v=reference.split(', Version=');select(name+'/'+v.split(',')[0])
  for g in project.findall('{*}ItemGroup'):
   if g.get('Condition')=="'$(IsPartialFacadeAssembly)' != 'true'":
    for e in g.findall('{*}Reference'):
     name=e.get('Include')
     if name not in item['source_dependency_inputs'] and name!='System.Numerics.Vectors':select(name+'/4.0.0.0')
  contract=Path('/clang64/lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts');private=next(p for p in refs if p.name=='System.Runtime.InteropServices.dll');assert private.parent.name=='ref'
  assert refs=={private if key=='System.Runtime.InteropServices/4.0.0.0' else contract/key/(key.split('/')[0]+'.dll') for key in closure}|dependencies
  assert all('/4.0.0.0/' in str(p) for p in refs-dependencies-{private})
 assert not (folder/'Analyzer.txt').read_text().strip();policy=(folder/'policy.txt').read_text().replace('\n',';').strip(';').split('|')
 assert policy[:2]==[tfm,'netstandard' if tfm=='netstandard2.0' else tfm] and policy[3:]==['1701;1702','7.3','true'] and 'DEBUG' not in policy[2]
 assert all(x in policy[2].split(';') for x in ['TRACE','RELEASE','netstandard','FEATURE_PORTABLE_SPAN'])
 assert ('netstandard11' in policy[2].split(';'))==(tfm=='netstandard1.1')
 assert sha(folder/'bin/Release/System.Memory.dll')==item['DLL_sha256'];profiles[profile]=dict(original_CSharp_inputs=102,exact_source_references=len(refs),DLL_sha256=item['DLL_sha256'],policy=policy)
assert private is not None;interop=private.parent.parent;ir=json.loads((interop/'results.json').read_text());assert sha(private)==ir['DLL_sha256'] and ir['exit_code']==0 and ir['reference_only']
for name,h in ir['original_file_sha256'].items():assert sha(interop/'source'/name)==h
raw=interop/'source/sbrp/src/referencePackages/src/system.runtime.interopservices/4.3.0/ref/netstandard1.1/System.Runtime.InteropServices.cs';old=interop/'source/corefx/src/System.Runtime.InteropServices/ref/System.Runtime.InteropServices.cs'
assert (interop/'Interop.Ported.cs').read_text()==runpy.run_path(str(here/'port-interop.py'))['port'](raw.read_text(encoding='utf-8-sig'),old.read_text(encoding='utf-8-sig'))
assert sha(interop/'Interop.Ported.cs')==ir['generated_port_sha256']
provenance=json.loads((here/'inputs/published-provenance.json').read_text());package=root/'feed/System.Memory.4.5.3.nupkg'
def groups(md):return {g.get('targetFramework'):[{k:(v.removeprefix('[').removesuffix(', )') if k=='version' else v) for k,v in d.attrib.items()} for d in g] for g in md.findall('{*}dependencies/{*}group')}
with zipfile.ZipFile(package) as z:
 md=E.fromstring(z.read('System.Memory.nuspec')).find('{*}metadata');assert md.findtext('{*}id')=='System.Memory' and md.findtext('{*}version')=='4.5.3' and md.find('{*}repository').get('commit')==record['source_commit']
 assert groups(md)==groups(E.parse(here/'inputs/original.nuspec').find('{*}metadata'))
 assets={n for n in z.namelist() if n.startswith(('lib/','ref/'))};assert assets==set(provenance['original_assets'])
 for name,h in provenance['original_assets'].items():
  if name.endswith('.dll'):assert hashlib.sha256(z.read(name)).hexdigest()==record['profiles'][name.rsplit('/',1)[0]]['DLL_sha256']
  else:assert hashlib.sha256(z.read(name)).hexdigest()==h
 for name in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:assert z.read(name)==(root/'source'/name).read_bytes()
 assert z.read('version.txt')==(record['source_commit']+'\r\n').encode() and z.read('useSharedDesignerContext.txt')==(root/'source/pkg/useSharedDesignerContext.txt').read_bytes()
 members={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
report=dict(original_source_files_verified=len(record['original_file_sha256']),unique_original_CSharp_inputs=len(unique),production_CSharp_changes=0,profiles=profiles,all_original_compile_selections_exact=True,all_exact_source_reference_and_dependency_bytes_verified=True,private_Interop4000_source_port_replayed_and_reference_bytes_verified=True,compiler_warning_release_and_portable_span_policy_verified=True,original_reference_asset_exclusion_and_dependency_groups_preserved=True,all_original_DLL_XML_empty_marker_version_and_license_assets_preserved=True,original_documentation_text_imported_from_pinned_published_package=True,original_buildtools_ILLink_task_replayed=False,package_sha256=sha(package),archive_members=members,full_historical_runtime_matrix_verified=False,full_dependency_goal_complete=False)
(root/'producer-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
