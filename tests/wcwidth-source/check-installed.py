"""Audit installed source bytes and execute fresh archive-based consumers and original cases."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

prefix,version,out=Path(sys.argv[1]).resolve(),sys.argv[2],Path(sys.argv[3]).resolve();out.mkdir();name='dotnet-wcwidth'+version.split('.')[0]+'-sources';doc=prefix/'share/doc'/name;here=Path(__file__).resolve().parent
manifest=json.loads((doc/'payload-sha256.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for rel,expected in manifest.items():assert sha(prefix/rel)==expected,rel
r=json.loads((doc/'source-results.json').read_text());archive=prefix/'lib/dotnet/library-packs'/('wcwidth.sources.'+version+'.nupkg');assert sha(archive)==r['archive_sha256']
prepared=out/'prepared';prepared.mkdir();shutil.copytree(doc/'validation-source',prepared/'source');r['archive']=archive.as_posix();(prepared/'results.json').write_text(json.dumps(r,indent=2)+'\n');commands=[]
for label,script,args in [('source-fixtures','check.py',[prepared,out/'source-check']),('NuGet-consumer','check-consumer.py',[prefix,version,out/'consumer'])]:
    command=[sys.executable,'-X','utf8',here/script,*args]
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=600)
    commands.append(dict(command=[str(p) for p in command],exit_code=result.returncode));assert result.returncode==0,label
(out/'results.json').write_text(json.dumps(dict(commands=commands,version=version,payload_files_verified=len(manifest),all_original_source_content_profiles_and_bytes_verified=True,fresh_original_NuGet_restore_and_Roslyn_compile_and_runtime_passed=True,unchanged_upstream_source_Fact_methods_executed=True,actual_NS2_public_and_internal_source_consumers_executed=True,original_MinVer_NuGetizer_analyzer_toolchain_replayed=False,all_original_runtime_hosts_tested=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS installed source package',version,'exact source content, unchanged fixtures, NS2 and fresh NuGet/MSBuild consumers')
