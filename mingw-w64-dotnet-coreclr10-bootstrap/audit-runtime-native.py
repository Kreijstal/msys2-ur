"""Native archive replay and exact native source/patch/Ninja-input audit."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile,re,os
root,here=map(Path,sys.argv[1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
archive=root/'runtime-v10.0.5.tar.gz';assert sha(archive)=='1692acae5e3adfd625452fbc9db4fd4e982c10e38189358ae245c74dd5514d7a'
record=json.loads((root/'source-inputs.json').read_text());replay=root/'audit-replay';assert not replay.exists();replay.mkdir();patches=['host-mingw.patch','coreclr-mingw.patch'];changed=set()
for name in patches:changed.update(re.findall(r'^\+\+\+ b/(.+)$',(here/name).read_text(),re.M))
verified=set()
with tarfile.open(archive) as t:
 assert t.pax_headers['comment']==record['runtime_source_commit']
 for m in t:
  if not m.isfile():continue
  name=m.name.partition('/')[2]
  if name in record['original_file_sha256'] or name in changed:
   data=t.extractfile(m).read()
   if name in record['original_file_sha256']:assert hashlib.sha256(data).hexdigest()==record['original_file_sha256'][name],name;verified.add(name)
   if name in changed:p=replay/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
assert verified==set(record['original_file_sha256'])
print('PASS all original runtime archive input hashes:',len(verified),flush=True)
for name in changed:(replay/name).parent.mkdir(parents=True,exist_ok=True)
# Patch is the MSYS executable but paths supplied here are native file names.
patch=Path('E:/msys64/usr/bin/patch.exe')
for name in patches:subprocess.run([str(patch),'--fuzz=0','--no-backup-if-mismatch','-p1','-i',str(here/name)],cwd=replay,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True)
for index,(name,h) in enumerate(record['original_file_sha256'].items(),1):
 assert sha(root/'r'/name)==(sha(replay/name) if name in changed else h),name
 if index%5000==0:print('Verified prepared source files',index,flush=True)
for name in changed:assert (root/'r'/name).read_bytes()==(replay/name).read_bytes(),name
for p,h in json.loads((root/'native-version-inputs.json').read_text())['generated_header_sha256'].items():assert sha(root/p)==h,p
build=root/'coreclr-build';ninja=Path('E:/msys64/clang64/bin/ninja.exe')
inputs=subprocess.check_output([str(ninja),'-C',str(build),'-t','inputs','coreclr','clrjit','mscorrc','clretwrc'],text=True).splitlines();sources={}
source_root=(root/'r').resolve()
for path in inputs:
 p=Path(path)
 if not p.is_absolute():p=build/p
 p=Path(os.path.normpath(str(p)))
 if p.is_relative_to(source_root):
  name=p.relative_to(source_root).as_posix();assert name in record['original_file_sha256'] or name in changed,name;sources[name]=sha(p)
# Derive coverage from actual built object outputs, rather than an assumed
# number of direct inputs (implicit headers are not in ninja -t inputs).
def key(path):return os.path.normpath(str(path)).replace('\\','/').lower()
built=set()
for line in (build/'.ninja_log').read_text().splitlines():
 fields=line.split('\t')
 if len(fields)==5:built.add(key(build/fields[3]))
compiled=[]
for command in json.loads((build/'compile_commands.json').read_text()):
 if key(Path(command['output'])) not in built:continue
 p=Path(command['file'])
 if p.is_relative_to(source_root):
  name=p.relative_to(source_root).as_posix();assert name in sources,('Built compile unit absent from audited Ninja inputs',name)
  compiled.append(name)
assert compiled and any(p.startswith('src/coreclr/vm/') for p in compiled) and any(p.startswith('src/coreclr/jit/') for p in compiled),compiled
print('PASS actual built native compile-unit coverage:',len(compiled),'units;',len(sources),'direct source inputs',flush=True)
result=dict(original_runtime_archive_files_verified=len(verified),replayed_source_patch_paths_verified=len(changed),coreclr_port_patch_sha256=sha(here/'coreclr-mingw.patch'),actual_source_ninja_input_files_verified=len(sources),actual_source_ninja_inputs_sha256=sources,actual_built_compilation_units_verified=len(compiled),actual_built_compilation_units=compiled,native_version_headers_verified=True,original_production_sources_removed=0,complete_runtime10=False,full_dependency_goal_complete=False)
(root/'native-source-audit.json').write_text(json.dumps(result,indent=2)+'\n')
