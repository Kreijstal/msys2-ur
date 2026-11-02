"""Verify unchanged source/project/targets and actual compiler source closure."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile,zipfile
root=Path(sys.argv[1]).resolve();source=root/'arcade';record=json.loads((root/'source-inputs.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected=record['archive_files'];found={}
with tarfile.open(root/'arcade-runtime10-4bf37ce6.tar.gz') as t:
 for m in t:
  name=m.name.partition('/')[2]
  if name in expected:found[name]=hashlib.sha256(t.extractfile(m).read()).hexdigest();assert sha(source/name)==expected[name]
assert found==expected
native_source=subprocess.check_output(['cygpath','-am',str(source)],text=True).strip()
lines=(root/'build/obj/Release/net8.0/Compile.txt').read_text(encoding='utf-8-sig').splitlines()
actual=[p.replace('\\','/')[len(native_source)+1:] for p in lines if p.replace('\\','/').lower().startswith(native_source.lower()+'/')]
assert set(actual)==set(record['original_cs']) and len(actual)==8
refs=(root/'build/obj/Release/net8.0/ReferencePath.txt').read_text(encoding='utf-8-sig').splitlines();feed=Path('/clang64/lib/dotnet/library-packs');verified={}
cache=root/'build/cache';native_cache=subprocess.check_output(['cygpath','-am',str(cache)],text=True).strip()
for value in refs:
 normalized=value.replace('\\','/')
 if not normalized.lower().startswith(native_cache.lower()+'/'):continue
 rel=normalized[len(native_cache)+1:];name,version,*tail=rel.split('/');archive=feed/(name+'.'+version+'.nupkg')
 assert archive.is_file(),archive
 with zipfile.ZipFile(archive) as z:assert (cache/rel).read_bytes()==z.read('/'.join(tail)),value
 assert (cache/name/version/(name+'.'+version+'.nupkg')).read_bytes()==archive.read_bytes()
 verified[rel]=sha(cache/rel)
assert any('microsoft.codeanalysis.csharp/4.14.0/' in n for n in verified)
product=root/'product';targets=source/'src/Microsoft.DotNet.GenFacades/build'
for p in targets.glob('*.targets'):assert (product/'build'/p.name).read_bytes()==p.read_bytes()
assert len(list(targets.glob('*.targets')))==4
checks=json.loads((root/'check/results.json').read_text());assert checks['missing_seed_rejected'] and checks['unsupported_api_execution_passed'] and checks['clear_reference_versions_passed']
result=dict(original_cs=8,original_archive_inputs_verified=len(expected),all_original_sources_and_targets_match=True,actual_compiler_original_inputs_match=True,actual_source_nuget_references=verified,original_target_files=4,production_cs_changes=0,original_frameworks=record['original_frameworks'],bootstrap_framework=record['bootstrap_framework'],declared_roslyn_version=record['declared_roslyn_version'],bootstrap_roslyn_version=record['bootstrap_roslyn_version'],declared_msbuild_tasks_version=record['declared_msbuild_tasks_version'],bootstrap_msbuild_version=record['bootstrap_msbuild_version'],full_original_tool_profiles_complete=False,full_dependency_goal_complete=False)
(root/'source-audit.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS eight actual original compiler inputs, archive hashes, source NuGet references and four unchanged original targets')
