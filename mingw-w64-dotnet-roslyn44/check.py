"""Build a fresh NS2 consumer and execute the original 4.4 compiler/WS APIs."""
from pathlib import Path
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E

root, out, check = (Path(p).resolve() for p in sys.argv[1:4])
installed=len(sys.argv)==5
assert not installed or Path(sys.argv[4]).resolve()==Path('/clang64/lib/dotnet/library-packs')
assert not check.exists(), check
check.mkdir()
here = Path(__file__).resolve().parent
base = subprocess.check_output(['cygpath', '-am', str(root)], text=True).strip()
def native(p):
    p=Path(p).resolve()
    if p.is_relative_to(root):return base+'/'+p.relative_to(root).as_posix()
    return subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
record = json.loads((out / 'source-inputs.json').read_text())
source = out / 'roslyn-source'
for name, suffix in [('Microsoft.CodeAnalysis', 'compiler-common'), ('Microsoft.CodeAnalysis.CSharp', 'compiler-csharp'), ('Microsoft.CodeAnalysis.Workspaces', 'common'), ('Microsoft.CodeAnalysis.CSharp.Workspaces', 'csharp')]:
    folder = (source / record['projects'][name]['original_project']).parent
    (check / ('api-' + suffix + '.txt')).write_text('\n'.join((folder / f).read_text(encoding='utf-8-sig') for f in ['PublicAPI.Shipped.txt', 'PublicAPI.Unshipped.txt']) + '\n')
resources = json.loads((out / 'localization.json').read_text())
(check / 'compiler-localization.json').write_text(json.dumps([r for r in resources if r['assembly'] in {'Microsoft.CodeAnalysis', 'Microsoft.CodeAnalysis.CSharp'}], ensure_ascii=False, indent=2) + '\n')
(check / 'source-items.json').write_text(json.dumps(record['projects'], indent=2) + '\n')
standard = check / 'standard-consumer'
standard.mkdir()
for folder, standard_target in [(standard, True), (check, False)]:
    tree = E.Element('Project', Sdk='Microsoft.NET.Sdk')
    pg = E.SubElement(tree, 'PropertyGroup')
    for k, v in dict(AssemblyName='StandardRoslyn44Consumer' if standard_target else 'Check', TargetFramework='netstandard2.0' if standard_target else 'net8.0', OutputType='Library' if standard_target else 'Exe', UseAppHost='false', EnableDefaultItems='false', EnableNETAnalyzers='false', NuGetAudit='false', LangVersion='preview', Nullable='disable', CscToolPath=native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')), CscToolExe='csc50.cmd').items():
        E.SubElement(pg, k).text = v
    items = E.SubElement(tree, 'ItemGroup')
    for path in ([here / 'inputs/StandardConsumer.cs'] if standard_target else [p for p in sorted((here / 'inputs').glob('*.cs')) if p.name not in {'StandardConsumer.cs','EvaluateRoslynProjects.cs'}]):
        E.SubElement(items, 'Compile', Include=native(path))
    E.SubElement(items, 'PackageReference', Include='Microsoft.CodeAnalysis.CSharp.Workspaces', Version='[4.4.0]')
    if not standard_target:
        E.SubElement(items, 'ProjectReference', Include='standard-consumer/Build.csproj')
    E.indent(tree)
    E.ElementTree(tree).write(folder / 'Build.csproj', encoding='utf-8', xml_declaration=True)
config=E.Element('configuration');feeds=E.SubElement(config,'packageSources');E.SubElement(feeds,'clear')
for i,path in enumerate(([out/'feed'] if not installed else [])+[Path('/clang64/lib/dotnet/library-packs')]):E.SubElement(feeds,'add',key='source'+str(i),value=native(path))
E.indent(config);E.ElementTree(config).write(check/'NuGet.config',encoding='utf-8',xml_declaration=True)
env = dict(os.environ, DOTNET_CLI_HOME=native(check / 'cli-home'), NUGET_PACKAGES=native(check / 'cache'), DOTNET_CLI_TELEMETRY_OPTOUT='1', MSBuildEnableWorkloadResolver='false')
dotnet = '/clang64/lib/dotnet/dotnet.exe'
with (check / 'build.log').open('w') as log:
    subprocess.run([dotnet, 'build', native(check / 'Build.csproj'), '-c', 'Release', '--configfile', native(check / 'NuGet.config'), '-p:UseSharedCompilation=false', '-v:minimal'], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
refs = subprocess.check_output(['cygpath', '-am', '/clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0'], text=True).strip()
command = [dotnet, native(check / 'bin/Release/net8.0/Check.dll'), refs, native(check), native(out / 'localization.json'), native(check / 'source-items.json')]
with (check / 'run.log').open('w') as log:
    result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
(check / 'run.exit').write_text(str(result.returncode) + '\n')
assert result.returncode == 0, (result.returncode, check / 'run.log')
(check / 'results.json').write_text(json.dumps(dict(command=command, exit_code=0, formal_pacman_installed=installed, full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS fresh Roslyn4.4 original compiler, Workspaces, NS2 consumer, API/resources and identities')
