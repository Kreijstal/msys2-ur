"""Build all original Runtime references and the complete NET462 facade."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

sbrp, corefx, out, prefix, compiler = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir(); here = Path(__file__).parent; dotnet = prefix / 'lib/dotnet/dotnet.exe'; commands = []
def run(label, command):
    command = [str(p) for p in command]; result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (label + '.log')).write_bytes(result.stdout); commands.append(dict(command=command, exit_code=result.returncode))
    assert result.returncode == 0, (label, result.stdout.decode('utf-8', errors='replace')[-6000:])
run('tools', [sys.executable, here / 'build-seed-tools.py', out / 'tools', prefix])
run('references', [sys.executable, here / 'build-references.py', sbrp, out / 'references', prefix, compiler])
run('restore', [dotnet, out / 'tools/RestoreReferenceAttributes/bin/Release/net8.0/RestoreReferenceAttributes.dll', here / 'inputs', out / 'references/raw', out / 'ref'])
run('framework-seeds', [sys.executable, here / 'build-framework-seeds.py', out / 'framework-seeds', out / 'tools', prefix, compiler])
run('facade', [sys.executable, here / 'build-facade.py', corefx, out / 'ref', out / 'framework-seeds', out / 'tools', out / 'facade', prefix, compiler])
folder = out / 'ref/System.Runtime/net462'; folder.mkdir(); shutil.copy2(out / 'facade/System.Runtime.dll', folder / 'System.Runtime.dll')
(out / 'results.json').write_text(json.dumps(dict(commands=commands, source_reference_archive_sha256=hashlib.sha256(sbrp.read_bytes()).hexdigest(), source_CoreFX_archive_sha256=hashlib.sha256(corefx.read_bytes()).hexdigest(),
    original_reference_profiles=4, original_NET462_forwarding_facades=1, original_reference_source_changes=0,
    original_binaries_executed_or_compiler_references=False, private_Framework_seeds_are_reference_only=True,
    historical_Framework_runtime_execution_verified=False, full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS four original Runtime source reference profiles and complete277-export NET462 facade built')
