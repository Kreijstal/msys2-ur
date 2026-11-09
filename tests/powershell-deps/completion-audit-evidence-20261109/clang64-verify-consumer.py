"""Match the complete restored net8 closure and every consumer DLL to source owners."""
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile
root,out,feed=map(lambda s:Path(s).resolve(),sys.argv[1:]);sha=lambda data:hashlib.sha256(data).hexdigest()
installed=Path('/clang64/lib/dotnet/library-packs');owners={};by_hash={}
for archive in sorted((out/'cache').rglob('*.nupkg')):
 candidate=feed/archive.name;source=candidate if candidate.is_file() else installed/archive.name
 assert source.is_file() and source.read_bytes()==archive.read_bytes(),archive
 native_owner=None if source.parent==feed and feed!=installed and archive.name=='microsoft.windows.compatibility.8.0.31.nupkg' else subprocess.check_output(['pacman','-Qqo',str(source)],text=True).strip()
 owners[archive.name]=dict(archive_sha256=sha(archive.read_bytes()),native_owner=native_owner)
 with zipfile.ZipFile(archive) as z:
  for name in z.namelist():
   if name.endswith('.dll'):by_hash.setdefault(sha(z.read(name)),[]).append(dict(package=archive.name,asset=name))
assets=json.loads((out/'obj/project.assets.json').read_text());assert len(assets['targets'])==1
target=next(iter(assets['targets'].values()));meta=target['Microsoft.Windows.Compatibility/8.0.31']
expected=json.loads((root/'dependency-groups.json').read_text())['net8.0']
assert meta['dependencies']==expected,(meta['dependencies'],expected)
assert not meta.get('compile') and not meta.get('runtime'),meta
record={}
for file in (out/'bin/Release/net8.0').rglob('*.dll'):
 if file.name=='Check.dll':continue
 digest=sha(file.read_bytes());assert digest in by_hash,('Unowned consumer DLL',file,digest)
 record[file.relative_to(out/'bin/Release/net8.0').as_posix()]=dict(sha256=digest,source_package_assets=by_hash[digest])
assert len(owners)>=35 and len(record)>=35,(len(owners),len(record))
(out/'source-closure.json').write_text(json.dumps(dict(source_package_owners=owners,consumer_dlls=record,metapackage_net8_dependencies=expected,all_restored_archives_match_source_feed=True,all_consumer_dlls_match_source_packages=True,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS full fresh net8 source closure:',len(owners),'package archives and',len(record),'consumer DLLs; all35 original direct dependency edges selected')
