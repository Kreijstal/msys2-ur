"""Cold compile, version, stage and localize all primary NET10 MSBuild projects."""
from pathlib import Path
import json,os,subprocess,sys

root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent;commands=[]
for label,script,args in [
 ('version','prepare-version.py',[root/'plan',root/'arcade-msbuild18-987d1a73.tar.gz',root/'version']),
 ('compile','build-all.py',[root/'plan',root/'build','-',root/'version/file-version.txt']),
 ('cli','check-cli.py',[root/'plan',root/'build',root/'cli']),
 ('localization','localize.py',[root/'plan',root/'build',root/'cli/stage',root/'localized']),
 ('parallel','check-parallel.py',[root/'localized/bin',root/'parallel'])]:
    command=[sys.executable,'-X','utf8',here/script,*args]
    print('RUN',label,flush=True)
    with (root/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
    commands.append(dict(label=label,command=[str(p) for p in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
(root/'build-results.json').write_text(json.dumps(dict(commands=commands,cold_source_build=True,all_six_primary_projects_built=True,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS cold primary MSBuild18 build,original version policy,CLI,53 satellites and parallel workers')
