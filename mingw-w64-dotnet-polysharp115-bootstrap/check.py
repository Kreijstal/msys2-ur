"""Run producer or fresh installed package validation."""
from pathlib import Path
import json
import subprocess
import sys

producer,check=(Path(p).resolve() for p in sys.argv[1:3]);check.mkdir()
installed=len(sys.argv)==4
feed=Path(sys.argv[3]).resolve() if installed else producer/'feed'
if installed:assert feed==Path('/clang64/lib/dotnet/library-packs')
here=Path(__file__).resolve().parent
commands=[]
for script,label in [('check-runtime.py','runtime'),('check-consumers.py','consumers'),('check-guards.py','guards')]:
    args=[str(feed),str(check/label)] if label=='guards' else [str(producer),str(check/label)]
    if label!='guards' and installed:args.append(str(feed))
    command=['/usr/bin/python3',str(here/script),*args]
    with (check/(label+'.log')).open('w') as log:
        result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
    commands.append(dict(command=command,exit_code=result.returncode))
    assert result.returncode==0,(label,check/(label+'.log'))
    print((check/(label+'.log')).read_text(),end='',flush=True)
(check/'results.json').write_text(json.dumps(dict(commands=commands,formal_pacman_installed=installed,runtime=json.loads((check/'runtime/results.json').read_text()),consumers=json.loads((check/'consumers/results.json').read_text()),guards=json.loads((check/'guards/results.json').read_text()),full_dependency_goal_complete=False),indent=2)+'\n')
