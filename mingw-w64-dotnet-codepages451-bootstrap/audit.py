"""Audit all five original implementations, source lineages, references and paths."""
from pathlib import Path
import functools,hashlib,json,subprocess,sys,xml.etree.ElementTree as E,zipfile
root=Path(sys.argv[1]).resolve();here=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();record=json.loads((root/'results.json').read_text());manifest=json.loads((here/'original-profile-requirements-20261031.json').read_text());matrix=json.loads((here/'inputs/source-contract-build-matrix.json').read_text());library='System.Text.Encoding.CodePages'
assert record['production_CSharp_changes']==0 and set(record['profiles'])==set(manifest['profiles']) and all(c['exit_code']==0 for c in record['commands'])
for tag,data in record['source_lineages'].items():
 for n,h in data['original_file_sha256'].items():assert sha(root/'sources'/tag/n)==h
native=functools.lru_cache(None)(lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip());posix=functools.lru_cache(None)(lambda s:Path(subprocess.check_output(['cygpath','-au',s],text=True).strip()).resolve());unique=set();profiles={}
for profile,item in record['profiles'].items():
 legacy=profile.startswith('legacy');windows=profile.endswith('windows');tag='legacy' if legacy else 'current';source=root/'sources'/tag;folder=root/'profiles'/profile;project=source/'src'/library/'src'/(library+'.csproj');tree=E.parse(project);expected={source/'src/Common/src/System/SR.cs'};group='' if legacy else 'netcoreapp2.0' if profile=='netcore2-windows' else 'netstandard';tfm='netstandard1.3' if legacy else 'netcoreapp2.0' if profile=='netcore2-windows' else 'netstandard2.0'
 for ig in tree.findall('{*}ItemGroup'):
  cond=ig.get('Condition','').strip()
  if not ig.findall('{*}Compile'):continue
  assert cond in ['',"'$(TargetsWindows)' == 'true'","'$(TargetsUnix)' == 'true'","'$(TargetGroup)' == 'netstandard' AND '$(TargetsWindows)' != 'true'"]
  if cond=="'$(TargetsWindows)' == 'true'" and not windows:continue
  if cond=="'$(TargetsUnix)' == 'true'" and windows:continue
  if cond=="'$(TargetGroup)' == 'netstandard' AND '$(TargetsWindows)' != 'true'" and (windows or group!='netstandard'):continue
  expected.update((project.parent/e.get('Include').replace('$(CommonPath)','../../Common/src').replace('\\','/')).resolve() for e in ig.findall('{*}Compile'))
 unique.update((tag,str(p.relative_to(source))) for p in expected);assert {str(p.relative_to(source)):sha(p) for p in expected}==item['original_CSharp_inputs']
 assert {posix(s) for s in (folder/'Compile.txt').read_text().splitlines() if s}==expected|{folder/'Version.cs',folder/'SR.Generated.cs'}
 refs={posix(s) for s in (folder/'ReferencePath.txt').read_text().splitlines() if s};assert {native(p):sha(p) for p in refs}==item['reference_sha256']
 if legacy:
  closure=set()
  def select(key):
   if key in closure:return
   closure.add(key)
   for ref in matrix[key]['references']:
    name,v=ref.split(', Version=');select(name+'/'+v.split(',')[0])
  for n,v in json.loads((project.parent/'project.json').read_text())['dependencies'].items():
   if n!='Microsoft.NETCore.Platforms':select(n+'/'+v+'.0')
  highest={}
  for key in closure:
   n,v=key.split('/')
   if n not in highest or tuple(map(int,v.split('.')))>tuple(map(int,highest[n].split('/')[1].split('.'))):highest[n]=key
  contracts=Path('/clang64/lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts');assert refs=={contracts/key/(key.split('/')[0]+'.dll') for key in highest.values()}
 else:
  dep=item['source_dependency_inputs'];file=folder/'source-dependencies/System.Runtime.CompilerServices.Unsafe.dll';package=Path('/clang64/lib/dotnet/library-packs')/dep['package'];assert sha(package)==dep['package_sha256'] and sha(file)==dep['DLL_sha256']
  with zipfile.ZipFile(package) as z:assert z.read(dep['asset'])==file.read_bytes()
  base=Path('/clang64/lib/dotnet/reference-packs/netcore20-contracts-bootstrap/ref') if tfm=='netcoreapp2.0' else Path('/clang64/lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0');assert refs==set(base.glob('*.dll'))|{file} and len(refs)==(11 if tfm=='netcoreapp2.0' else 114)
 assert not (folder/'Analyzer.txt').read_text().strip();policy=(folder/'policy.txt').read_text().replace('\n',';').strip(';').split('|');assert policy[:4]==[tfm,group,str(windows).lower(),str(not windows).lower()] and policy[5:]==['1701;1702','6' if legacy else '7.3','true'] and 'DEBUG' not in policy[4]
 assert sha(folder/'bin/Release'/(library+'.dll'))==item['DLL_sha256'];assert sha(project.parent/'Data/codepages.nlp')==item['codepages_nlp_sha256']
 assert set(item['original_paths'])==set(manifest['profiles'][profile]['original_paths'])
 for path in item['original_paths']:assert sha(root/'assets'/path)==item['DLL_sha256']
 profiles[profile]=dict(source_commit=item['source_commit'],original_CSharp_inputs=len(expected),exact_source_references=len(refs),DLL_sha256=item['DLL_sha256'],original_paths=item['original_paths'],policy=policy)
package=root/'feed/System.Text.Encoding.CodePages.4.5.1.nupkg';original=E.parse(here/'inputs/original.nuspec').find('{*}metadata');provenance=json.loads((here/'inputs/published-provenance.json').read_text())
def groups(md):return {g.get('targetFramework'):[{k:(v.removeprefix('[').removesuffix(', )') if k=='version' else v) for k,v in d.attrib.items()} for d in g] for g in md.findall('{*}dependencies/{*}group')}
with zipfile.ZipFile(package) as z:
 md=E.fromstring(z.read('System.Text.Encoding.CodePages.nuspec')).find('{*}metadata');assert groups(md)==groups(original) and md.findtext('{*}version')=='4.5.1'
 assert {n for n in z.namelist() if n.startswith(('lib/','ref/','runtimes/'))}==set(provenance['original_assets'])
 for name in provenance['original_assets']:
  if name.endswith('.dll'):assert z.read(name)==(root/'assets'/name).read_bytes()
  else:assert z.read(name)==b''
 for name in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:assert z.read(name)==(root/'sources/current'/name).read_bytes()
 assert z.read('version.txt')==b'99ce22c306b07f99ddae60f443d23a983ae78f7b\r\n' and z.read('useSharedDesignerContext.txt')==(root/'sources/current/pkg/useSharedDesignerContext.txt').read_bytes()
 members={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
report=dict(original_source_files_verified=sum(len(d['original_file_sha256']) for d in record['source_lineages'].values()),unique_original_CSharp_inputs_across_lineages=len(unique),production_CSharp_changes=0,profiles=profiles,original_source_selections_and_exact_reference_bytes_verified=True,original_warning_release_platform_and_target_policy_verified=True,all_five_distinct_implementations_and_eight_original_DLL_paths_preserved=True,original_dependency_groups_and_twelve_empty_markers_preserved=True,all_original_alias_groups_byte_identical=True,package_sha256=sha(package),archive_members=members,original_buildtools_host_replayed=False,full_dependency_goal_complete=False)
(root/'producer-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
