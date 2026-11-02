"""Run the pinned upstream packaging generators on source-built analyzer assemblies.

The nonshipping NET7 generator is compiled/hosted on the installed source NET10
bootstrap. Production analyzer assemblies retain their original NS2 profile.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

archive, build, codefix, out = (Path(p).resolve() for p in sys.argv[1:])
out.mkdir()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == '49a992347546aef48cb31673b294bd1b10c30e68bbb53be61d411bb0d7219e1e'
commit = '22ea6422f85b05ca0793cc3b76375487be407f5d'
source = out / 'source'
source.mkdir()
original_files = {}
with tarfile.open(archive) as full:
    prefix = 'roslyn-analyzers-' + commit + '/'
    for member in full:
        if not member.isfile():
            continue
        assert member.name.startswith(prefix)
        relative = member.name[len(prefix):]
        if not any(relative.startswith(d) for d in ['src/Tools/', 'src/Utilities/', 'src/Microsoft.CodeAnalysis.Analyzers/Core/MetaAnalyzers/', 'assets/', 'docs/']):
            continue
        if Path(relative).suffix.lower() in {'.dll', '.exe', '.pdb', '.nupkg', '.snk', '.lib', '.obj', '.a', '.winmd'}:
            continue
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(full.extractfile(member).read())
        original_files[relative] = sha(path)
prefix = Path(subprocess.check_output(['cygpath', '-am', '/clang64'], text=True).strip())
host = prefix / 'lib/dotnet10/dotnet.exe'
compiler = prefix / 'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
refs = sorted((prefix / 'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'))
assert len(refs) == 167
native = lambda p: Path(p).resolve().as_posix()
env = dict(os.environ, DOTNET_ROOT=native(host.parent), DOTNET_ROOT_X64=native(host.parent))
commands, tools = [], {}
binary = out / 'bin'
binary.mkdir()
for path in (codefix / 'bin').glob('*.dll'):
    if path.name != 'Check.dll':
        shutil.copyfile(path, binary / path.name)
for tool in ['GenerateDocumentationAndConfigFiles', 'GenerateAnalyzerNuspec']:
    folder = source / 'src/Tools' / tool
    project = E.parse(folder / (tool + '.csproj'))
    assert project.findtext('.//TargetFramework') == 'net7.0'
    inputs = set(folder.glob('*.cs'))
    for item in project.findall('.//Compile'):
        relative = item.get('Include').replace('\\', '/')
        inputs.add((folder / relative).resolve())
    assert all(p.is_relative_to(source) and p.is_file() for p in inputs)
    selected = {p.name: p for p in [*binary.glob('*.dll'), *refs] if p.name not in ['Check.dll', 'GenerateDocumentationAndConfigFiles.dll', 'GenerateAnalyzerNuspec.dll']}
    response = out / (tool + '.rsp')
    args = ['/nostdlib+', '/target:exe', '/nullable:enable', '/debug:portable', '/out:"' + native(binary / (tool + '.dll')) + '"']
    args += ['/reference:"' + native(p) + '"' for p in selected.values()]
    args += ['"' + native(p) + '"' for p in sorted(inputs)]
    response.write_text('\n'.join(args) + '\n')
    cmd = [host, compiler, '-noconfig', '@' + native(response)]
    with (out / (tool + '-compile.log')).open('w', encoding='utf-8') as log:
        result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=env, timeout=180)
    commands.append(dict(command=[str(p) for p in cmd], exit_code=result.returncode))
    assert result.returncode == 0, tool
    (binary / (tool + '.runtimeconfig.json')).write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0', framework=dict(name='Microsoft.NETCore.App', version='10.0.5')))))
    tools[tool] = dict(original_framework='net7.0', bootstrap_framework='net10.0', source_changes=0,
        original_source_sha256={p.relative_to(source).as_posix():sha(p) for p in sorted(inputs)}, output_sha256=sha(binary / (tool + '.dll')))
artifacts = out / 'artifacts'
names = ['Microsoft.CodeAnalysis.PublicApiAnalyzers', 'Microsoft.CodeAnalysis.PublicApiAnalyzers.CodeFixes']
for name in names:
    folder = artifacts / name / 'Release/netstandard2.0'
    folder.mkdir(parents=True)
    for path in (build / 'bin').glob(name + '.*'):
        if path.is_file():shutil.copyfile(path, folder / path.name)
    if not name.endswith('CodeFixes'):
        for culture in (build / 'bin').iterdir():
            if culture.is_dir():shutil.copytree(culture, folder / culture.name)
        release = folder / 'AnalyzerReleases' / name
        release.mkdir(parents=True)
        for path in (build / 'snapshot/source/src/PublicApiAnalyzers/Core/Analyzers').glob('AnalyzerReleases.*.md'):
            shutil.copyfile(path, release / path.name)
paths = {name:out / name for name in ['rulesets','editorconfig','globalconfig','build','documentation']}
for p in paths.values():p.mkdir()
args = ['-validateOnly:false', native(paths['rulesets']), native(paths['editorconfig']), native(paths['globalconfig']), native(artifacts), 'Release', 'netstandard2.0', ';'.join(n+'.dll' for n in names), native(paths['build']), names[0]+'.props', native(paths['build']), names[0]+'.targets', '', native(paths['documentation']), names[0]+'.md', native(paths['documentation']), names[0]+'.sarif', '3.3.4', names[0], 'false', 'false', 'false', 'true']
cmd = [host, binary / 'GenerateDocumentationAndConfigFiles.dll', *args]
with (out / 'generate.log').open('w', encoding='utf-8') as log:
    result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=env, timeout=180)
commands.append(dict(command=[str(p) for p in cmd], exit_code=result.returncode))
assert result.returncode == 0, ('generate', result.returncode)
files = {p.relative_to(out).as_posix():sha(p) for folder in paths.values() for p in sorted(folder.rglob('*')) if p.is_file()}
(out / 'results.json').write_text(json.dumps(dict(commands=commands, tools=tools, original_source_sha256=original_files, generated_file_sha256=files, original_NET7_nonshipping_generators_bootstrapped_on_NET10=True, production_NS2_framework_preserved=True, full_dependency_goal_complete=False), indent=2)+'\n')
print('PASS original unmodified packaging generators;',len(files),'generated config/documentation files')
