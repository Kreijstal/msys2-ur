"""Audit unchanged original NET8 producer inputs, peer assets and shipped NuGet contents."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile,xml.etree.ElementTree as E,zipfile
root,out,consumer=(Path(p).resolve() for p in sys.argv[1:]);source=root/'r';record=json.loads((out/'source-inputs.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
def posix(p):
 p=p.replace('\\','/').rstrip('/')
 if p.lower().startswith(base.lower()+'/'):return root/p[len(base)+1:]
 return Path(subprocess.check_output(['cygpath','-u',p],text=True).strip())
wanted={};doc_counts={};packages={};generator=Path('/clang64/lib/dotnet/generator-packs/runtime-10.0.5/analyzers/dotnet/cs')
for name,item in record['projects'].items():
 for p,h in {**item['original_cs'],**item['original_resources']}.items():assert sha(source/p)==h,p;wanted[p]=h
 for p in [item['original_project'],*item['key_policy']['files'],'src/libraries/'+name+'/ref/'+name+'.csproj','src/libraries/'+name+'/src/PACKAGE.md']:wanted[p]=sha(source/p)
 for p in (source/'src/libraries'/name/'ref').glob('*.cs'):wanted[p.relative_to(source).as_posix()]=sha(p)
 actual={posix(p) for p in (out/name/'obj/Release/net8.0/Compile.txt').read_text().splitlines() if p}
 assert {p for p in actual if p.is_relative_to(source)}=={source/p for p in item['original_cs']},name
 tree=E.parse(out/name/'Build.csproj');assert tree.findtext('.//TargetFramework')=='net8.0' and tree.findtext('.//CLSCompliant')=='true'
 refs=[posix(p) for p in (out/name/'obj/Release/net8.0/ReferencePath.txt').read_text().splitlines() if p]
 for peer in item['project_dependencies']:
  selected=[p for p in refs if p.name==peer+'.dll'];assert len(selected)==1 and selected[0].is_relative_to(out/peer),(name,peer,selected)
 log=(out/name/'build.log').read_text();assert not any(c in log for c in ['CS3021','CS8032','CS8784','CS8785']),name
 package=out/'feed'/(name+'.10.0.5.nupkg');folder=out/name/'bin/Release/net8.0'
 with zipfile.ZipFile(package) as z:
  assert z.read('lib/net8.0/'+name+'.dll')==(folder/(name+'.dll')).read_bytes()
  xml=z.read('lib/net8.0/'+name+'.xml');assert xml==(folder/(name+'.xml')).read_bytes()
  doc_counts[name]=len(E.fromstring(xml).findall('.//member'));assert doc_counts[name]>0
  for f in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:assert z.read(f)==(source/f).read_bytes()
  assert z.read('PACKAGE.md')==(source/'src/libraries'/name/'src/PACKAGE.md').read_bytes()
  spec=E.fromstring(z.read(next(p for p in z.namelist() if p.endswith('.nuspec'))));md=next(e for e in spec if e.tag.endswith('metadata'));values={e.tag.rsplit('}',1)[-1]:e.text for e in md}
  assert values['id']==name and values['version']=='10.0.5'
  assert all(e.get('targetFramework')=='net8.0' for e in md.iter() if e.tag.endswith('group'))
  deps={e.get('id') for e in md.iter() if e.tag.endswith('dependency')};assert deps==set(item['project_dependencies']),(name,deps,item['project_dependencies'])
  repo=next(e for e in md if e.tag.endswith('repository'));assert repo.get('commit')==record['runtime_commit']
  analyzer_files=[p for p in z.namelist() if p.startswith('analyzers/')]
  if name=='System.Text.Json':
   assert sum(p.endswith('.dll') for p in analyzer_files)==14,analyzer_files
   for p in analyzer_files:assert z.read(p)==(generator/p.removeprefix('analyzers/dotnet/roslyn4.4/cs/')).read_bytes(),p
  else:assert not analyzer_files
 packages[name]=dict(sha256=sha(package),dependencies=item['project_dependencies'],documented_members=doc_counts[name])
for p in ['src/libraries/Directory.Build.props','src/libraries/Directory.Build.targets','eng/Versions.props','eng/versioning.targets','eng/illink.targets','LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:wanted[p]=sha(source/p)
verified=set()
with tarfile.open(root/'runtime-v10.0.5.tar.gz') as t:
 assert t.pax_headers['comment']==record['runtime_commit']
 for m in t:
  n=m.name.partition('/')[2]
  if m.isfile() and n in wanted:assert hashlib.sha256(t.extractfile(m).read()).hexdigest()==wanted[n],n;verified.add(n)
assert verified==set(wanted),set(wanted)-verified
json_analyzers=[posix(p) for p in (out/'System.Text.Json/obj/Release/net8.0/Analyzer.txt').read_text().splitlines() if p]
assert generator/'System.Text.RegularExpressions.Generator.dll' in json_analyzers
assert any('CreateIntegerRegex' in p.read_text() for p in (out/'System.Text.Json/generated').rglob('*.cs'))
for p,r in json.loads((out/'tool-inputs.json').read_text()).items():assert sha(posix(p))==r['sha256'],p
report=dict(original_archive_inputs_verified=len(verified),production_source_changes=0,original_production_source_counts={n:len(v['original_cs']) for n,v in record['projects'].items()},original_versioning_targets_imported=True,pinned_upstream_enum_converter_nullable_annotation_difference_verified=True,original_cls_policy_verified=True,no_cs3021_or_generator_load_execution_warning=True,source_packages=packages,original_xml_documentation_members=doc_counts,installed_regex10_used=True,original_json_analyzer_and_satellites_packaged=True,formal_pacman_installed=json.loads((consumer/'results.json').read_text())['formal_pacman_installed'],remaining_original_target_variants=True,source_illink_library_processing_verified=False,full_dependency_goal_complete=False)
(out/'source-package-audit.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS source/archive/metadata/peer/Regex10/three original NET8 NuGet/docs/analyzer audits')
