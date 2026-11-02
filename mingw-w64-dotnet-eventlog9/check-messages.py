"""Validate the selected source message DLL using Windows' native resource APIs."""
from pathlib import Path
import json,subprocess,sys,shutil,hashlib
assembly,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent;prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());copy=out/assembly.name;shutil.copyfile(assembly,copy);commands=[]
def run(label,command):
 with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(label=label,command=[str(x) for x in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
run('compile',[prefix/'bin/clang.exe','-std=c11','-Wall','-Wextra','-Werror','-municode',here/'inputs/native-messages.c','-o',out/'native-messages.exe'])
run('execute',[out/'native-messages.exe',copy])
(out/'results.json').write_text(json.dumps(dict(commands=commands,source_message_assembly_sha256=hashlib.sha256(copy.read_bytes()).hexdigest(),message_ids_checked=65536,unicode_insertions_passed=True,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS all65536 selected message DLL entries through independent native FormatMessage')
