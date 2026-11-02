"""Audit original source selections, partial facade projection, references and package."""
from pathlib import Path
import functools,hashlib,json,subprocess,sys,urllib.parse,xml.etree.ElementTree as E,zipfile
root=Path(sys.argv[1]).resolve();here=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();record=json.loads((root/'results.json').read_text())
assert record['source_commit']=='8321c729934c0f8be754953439b88e6e1c120c24' and record['production_CSharp_changes']==0
for n,h in record['original_file_sha256'].items():assert sha(root/'source'/n)==h,n
posix=functools.lru_cache(None)(lambda s:Path(subprocess.check_output(['cygpath','-au',s],text=True).strip()).resolve());native=functools.lru_cache(None)(lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip())
assert set(record['profiles'])=={k+'/'+t for k in ['lib','ref'] for t in ['netstandard1.0','netstandard2.0','net46']}
profiles={};unique=set()
for profile,item in record['profiles'].items():
 kind,tfm=profile.split('/');folder=root/kind/tfm;original=root/'source/src/System.Numerics.Vectors'/('src' if kind=='lib' else 'ref')/'System.Numerics.Vectors.csproj';project=E.parse(original)
 expected=set()
 for group in project.findall('{*}ItemGroup'):
  cond=group.get('Condition','')
  if cond and group.findall('{*}Compile'):
   if cond=="'$(IsPartialFacadeAssembly)' != 'true'" and tfm=='net46':continue
   assert cond in ["'$(IsPartialFacadeAssembly)' != 'true'","'$(IsPartialFacadeAssembly)' == 'true' OR $(TargetGroup.StartsWith('netstandard'))"]
  expected.update((original.parent/e.get('Include').replace('\\','/')).resolve() for e in group.findall('{*}Compile'))
 if kind=='lib':expected.add(root/'source/src/Common/src/System/SR.cs')
 assert len(expected)==(8 if tfm=='net46' else 18) if kind=='lib' else len(expected)==1
 unique.update(expected);assert {str(p.relative_to(root/'source')):sha(p) for p in expected}==item['original_CSharp_inputs']
 actual={posix(s) for s in (folder/'Compile.txt').read_text().splitlines() if s};generated={folder/'Version.cs'}|({folder/'SR.Generated.cs'} if kind=='lib' else set())
 if kind=='ref' and tfm=='net46':
  assert actual=={folder/'Reference.Projected.cs',folder/'Version.cs'}
  output=folder/'Reference.AuditProjection.cs';subprocess.run(['/clang64/lib/dotnet/dotnet.exe',native(root/'projection-tool/bin/Release/net8.0/Project.dll'),native(next(iter(expected))),native(output)],check=True,stdout=subprocess.DEVNULL);assert output.read_bytes()==(folder/'Reference.Projected.cs').read_bytes()
 else:assert actual==expected|generated
 refs={posix(s) for s in (folder/'ReferencePath.txt').read_text().splitlines() if s};assert {native(p):sha(p) for p in refs}==item['reference_sha256']
 if tfm=='net46':assert refs=={Path('/clang64/lib/dotnet/reference-packs/netframework46-contracts-bootstrap/ref')/n for n in ['mscorlib.dll','System.Numerics.dll']}
 elif tfm=='netstandard2.0':assert len(refs)==113 and all(p.parent==Path('/clang64/lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0') for p in refs)
 else:
  matrix=json.loads((here/'inputs/source-contract-build-matrix.json').read_text());closure=set()
  def select(key):
   if key in closure:return
   closure.add(key)
   for r in matrix[key]['references']:
    name,v=r.split(', Version=');select(name+'/'+v.split(',')[0])
  roots=['System.Runtime'] if kind=='ref' else ['System.Diagnostics.Contracts','System.Diagnostics.Tools','System.Globalization','System.Resources.ResourceManager','System.Runtime','System.Runtime.Extensions']
  for name in roots:select(name+'/4.0.0.0')
  contracts=Path('/clang64/lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts');assert refs=={contracts/k/(k.split('/')[0]+'.dll') for k in closure}
 assert not (folder/'Analyzer.txt').read_text().strip();policy=(folder/'policy.txt').read_text().replace('\n',';').strip(';').split('|');assert policy[:2]==[tfm,'netstandard' if tfm=='netstandard2.0' else tfm] and policy[3:]==['1701;1702','7.3','true'] and 'DEBUG' not in policy[2]
 if tfm=='net46':
  props=E.parse(folder/'Library.csproj');assert props.findtext('.//AutomaticallyUseReferenceAssemblyPackages')=='false';assert props.findtext('.//FrameworkPathOverride')==native(next(iter(refs)).parent)
 assert sha(folder/'bin/Release/System.Numerics.Vectors.dll')==item['DLL_sha256']
 profiles[profile]=dict(original_CSharp_inputs=len(expected),exact_source_references=len(refs),DLL_sha256=item['DLL_sha256'],policy=policy)
assert all(c['exit_code']==0 for c in record['commands'])
assert E.parse(root/'source/Packaging.props').findtext('.//{*}SkipValidatePackageTargetFramework')=='true'
pack_policy=E.parse(root/'archive/Archive.csproj')
assert pack_policy.findtext('.//NoWarn')=='NU5128;NU5130'
assert pack_policy.findtext('.//TreatWarningsAsErrors')=='true'
provenance=json.loads((here/'inputs/published-provenance.json').read_text());package=root/'feed/System.Numerics.Vectors.4.4.0.nupkg'
with zipfile.ZipFile(package) as z:
 members={urllib.parse.unquote(n):n for n in z.namelist()};assert len(members)==len(z.namelist())
 md=E.fromstring(z.read('System.Numerics.Vectors.nuspec')).find('{*}metadata');assert md.findtext('{*}id')=='System.Numerics.Vectors' and md.findtext('{*}version')=='4.4.0' and md.find('{*}repository').get('commit')==record['source_commit']
 groups={g.get('targetFramework'):[{k:(v.removeprefix('[').removesuffix(', )') if k=='version' else v) for k,v in d.attrib.items()} for d in g] for g in md.findall('{*}dependencies/{*}group')};assert groups==provenance['original_dependency_attributes']
 assert {n for n in members if n.endswith('.dll')}=={urllib.parse.unquote(n) for n in provenance['DLL_asset_sha256']}
 for name in provenance['DLL_asset_sha256']:
  decoded=urllib.parse.unquote(name);kind,tfm,file=decoded.split('/');assert z.read(members[decoded])==(root/kind/tfm/'bin/Release'/file).read_bytes()
 for name,h in provenance['XML_asset_sha256'].items():assert hashlib.sha256(z.read(members[urllib.parse.unquote(name)])).hexdigest()==h
 for name in provenance['empty_markers']:assert z.read(members[name])==b''
 assert z.read(members['lib/netstandard1.0/System.Numerics.Vectors.dll'])==z.read(members['lib/portable-net45+win8+wp8+wpa81/System.Numerics.Vectors.dll'])
 for lic in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:assert z.read(lic)==(root/'source'/lic).read_bytes()
 assert z.read('version.txt')==(record['source_commit']+'\r\n').encode() and z.read('useSharedDesignerContext.txt')==(root/'source/pkg/useSharedDesignerContext.txt').read_bytes()
 archive_members={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
report=dict(original_source_files_verified=len(record['original_file_sha256']),unique_original_CSharp_inputs=len(unique),production_CSharp_changes=0,profiles=profiles,original_compile_selections_and_reference_bytes_verified=True,NET46_reference_projection_replayed_and_equal=True,original_dependency_groups_preserved=True,all_seven_original_DLL_and_XML_profiles_preserved=True,all_fourteen_original_empty_markers_preserved=True,portable_alias_DLL_byte_identical_to_NS10=True,original_SkipValidatePackageTargetFramework_translated_to_NU5128_NU5130=True,package_sha256=sha(package),archive_members=archive_members,full_upstream_suite_run=False,full_historical_runtime_matrix_verified=False,full_dependency_goal_complete=False)
(root/'producer-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
