"""Verify staged/installed payload bytes, fresh NuGet restore and actual analyzer/fixer execution."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile

prefix, out = (Path(p).resolve() for p in sys.argv[1:])
out.mkdir()
doc = prefix / 'share/doc/dotnet-publicapi334-bootstrap'
here = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((doc / 'payload-sha256.json').read_text())
for rel, expected in manifest.items():assert sha(prefix / rel) == expected, rel
archive = json.loads((doc / 'archives.json').read_text())
assert sha(prefix / archive['archive']) == archive['sha256']
with zipfile.ZipFile(prefix / archive['archive']) as z:
    assert {n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()} == archive['members']
py = Path(sys.executable)
commands = []
def run(name, args):
    cmd = [py, '-X', 'utf8', here / name, *args]
    with (out / (name + '.log')).open('w', encoding='utf-8') as log:
        result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=420)
    commands.append(dict(command=[str(p) for p in cmd], exit_code=result.returncode))
    assert result.returncode == 0, name
run('restore-package.py', [prefix, out / 'restore'])
records = json.loads((out / 'restore/results.json').read_text())
restored = records['actual_source_packages']['Microsoft.CodeAnalysis.PublicApiAnalyzers']
assert restored['archive_sha256'] == archive['sha256']
cache = out / 'restore/cache/microsoft.codeanalysis.publicapianalyzers/3.3.4'
cached = cache / 'microsoft.codeanalysis.publicapianalyzers.3.3.4.nupkg'
assert sha(cached) == archive['sha256']
build = out / 'restored-analyzer'
binary = build / 'bin'
binary.mkdir(parents=True)
with zipfile.ZipFile(cached) as z:
    for member, expected in archive['members'].items():
        assert hashlib.sha256(z.read(member)).hexdigest() == expected
        if member.startswith('analyzers/dotnet/'):
            target = binary / member[len('analyzers/dotnet/'):]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(member))
shutil.copyfile(doc / 'build-results.json', build / 'results.json')
localized = out / 'localized'
localized.mkdir()
shutil.copyfile(doc / 'resource-expected.json', localized / 'expected.json')
shutil.copyfile(doc / 'localization-results.json', localized / 'results.json')
run('check-cli.py', [build, out / 'cli'])
run('check-codefix.py', [build, out / 'restore', out / 'codefix'])
run('check-resources.py', [build, localized, out / 'resources'])
# NuGet must select the package build imports as well as the analyzer files.
props = (out / 'restore/obj/Dependencies.proj.nuget.g.props').read_text()
targets = (out / 'restore/obj/Dependencies.proj.nuget.g.targets').read_text()
assert 'Microsoft.CodeAnalysis.PublicApiAnalyzers.props' in props
assert 'Microsoft.CodeAnalysis.PublicApiAnalyzers.targets' in targets
(out / 'results.json').write_text(json.dumps(dict(commands=commands, payload_files_verified=len(manifest), archive_members_verified=len(archive['members']), fresh_source_NuGet_cache_bytes_verified=True, generated_NuGet_build_imports_selected=True, actual_cached_analyzer_CLI_and_codefix_execution=True, resources_and_PDBs_verified=True, original_Roslyn12_host_compatibility_verified=False, full_dependency_goal_complete=False), indent=2)+'\n')
print('PASS installed payload, fresh exact source restore, cached analyzer/fix-all/resource execution and build imports')
