"""Build the complete seven-parent source payload with original identities."""
from pathlib import Path
import json
import shutil
import subprocess
import sys

sbrp,corefx,out,prefix,compiler=(Path(p).resolve() for p in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).parent;commands=[]
def run(label,command):
    command=[str(p) for p in command];r=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/(label+'.log')).write_bytes(r.stdout);commands.append(dict(command=command,exit_code=r.returncode));assert r.returncode==0,(label,r.stdout.decode(errors='replace')[-6000:])
run('references',[sys.executable,here/'build.py',sbrp,corefx,out/'references',prefix,compiler])
run('restore',[sys.executable,here/'finish.py',out/'references',out/'finished',prefix])
run('tools',[sys.executable,here/'build-seed-tools.py',out/'tools',prefix])
run('Framework-seeds',[sys.executable,here/'build-framework-seeds.py',out/'framework-seeds',out/'tools',prefix,compiler])
run('facades',[sys.executable,here/'build-facades.py',corefx,out/'finished',out/'framework-seeds',out/'tools',out/'facades',prefix,compiler])
shutil.copytree(out/'finished/ref',out/'ref');shutil.copytree(out/'facades/ref',out/'ref',dirs_exist_ok=True)
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_reference_profiles=12,original_Framework_facades=7,source_socket_accept_result_projection=True,source_RuntimeExtensions_two_nested_export_projection=True,private_reference_contracts_are_not_runtime_or_NuGet_replacements=True,publisher_binaries_executed_or_compiler_inputs=False,full_dependency_goal_complete=False),indent=2)+'\n')
