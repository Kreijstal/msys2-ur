"""Check every native package byte against the audited source metapackage build."""
from pathlib import Path
import argparse,hashlib,json,subprocess,tarfile,zipfile
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('artifact',type=Path);parser.add_argument('src',type=Path);parser.add_argument('--output',type=Path);args=parser.parse_args()
src=args.src.resolve();prepared=src/'prepared';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
package=prepared/'feed/microsoft.windows.compatibility.8.0.31.nupkg';proof=json.loads((prepared/'package-audit.json').read_text());assert sha(package)==proof['package_sha256']
assert proof['full_original_and_published_dependency_groups_match'] and proof['total_dependency_entries']==191
with zipfile.ZipFile(package) as z:
 assert {name:hashlib.sha256(z.read(name)).hexdigest() for name in z.namelist()}==proof['nuget_entry_sha256']
closure=json.loads((src/'consumer/source-closure.json').read_text());assert closure['all_restored_archives_match_source_feed'] and closure['all_consumer_dlls_match_source_packages']
assert len(closure['metapackage_net8_dependencies'])==35
doc='clang64/share/doc/dotnet-windows-compatibility/';expected={'clang64/lib/dotnet/library-packs/'+package.name:sha(package)}
for name in ['source-inputs','build-audit','package-audit','dependency-groups']:expected[doc+name+'.json']=sha(prepared/(name+'.json'))
for name in ['README.md','Check.cs','check.sh','verify-consumer.py','check-installed.sh']:expected[doc+name]=sha(src/name)
expected['clang64/share/licenses/dotnet-windows-compatibility/LICENSE']=sha(prepared/'source/LICENSE')
expected['clang64/share/licenses/dotnet-windows-compatibility/Arcade-LICENSE.TXT']=sha(prepared/'Arcade-LICENSE.TXT')
actual={};fields={}
with subprocess.Popen(['zstd','-dc',str(args.artifact)],stdout=subprocess.PIPE) as process:
 with tarfile.open(fileobj=process.stdout,mode='r|') as archive:
  for member in archive:
   if member.isdir():continue
   assert member.isfile(),member.name;data=archive.extractfile(member).read()
   if member.name=='.PKGINFO':
    for line in data.decode().splitlines():
     key,separator,value=line.partition(' = ')
     if separator:fields.setdefault(key,[]).append(value)
   elif member.name.startswith('.'):assert member.name in {'.BUILDINFO','.MTREE'},member.name
   else:actual[member.name]=hashlib.sha256(data).hexdigest()
 while process.stdout.read(1024*1024):pass
 assert process.wait()==0
assert fields['pkgname']==['mingw-w64-clang-x86_64-dotnet-windows-compatibility'] and fields['pkgver']==['8.0.31-1']
declared={line.split(' = ',1)[1].strip() for line in (src.parent/'.SRCINFO').read_text().splitlines() if line.strip().startswith('depends = ')}
assert set(fields['depend'])==declared and len(declared)==39
assert actual==expected,(sorted(set(expected)-set(actual)),sorted(set(actual)-set(expected)),[name for name in actual.keys()&expected.keys() if actual[name]!=expected[name]])
result=dict(native_artifact=args.artifact.name,native_artifact_sha256=sha(args.artifact),nuget_metapackage_sha256=sha(package),native_dependency_packages=39,nuget_dependency_entries=191,framework_groups=5,net8_restored_source_packages=len(closure['source_package_owners']),source_matched_consumer_dlls=len(closure['consumer_dlls']),exact_native_file_sha256=actual,installed_ownership_verified=False,full_native_sqlclient_compatibility=False,full_dependency_goal_complete=False)
if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n')
print('PASS exact native metapackage/provenance/license bytes and all39 source owner dependencies;191 metadata entries and fresh source closure; installed check remains required')
