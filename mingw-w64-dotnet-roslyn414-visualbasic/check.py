"""Fresh source-only consumer of the original VB compiler and language services."""
from pathlib import Path
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E

root,out,check=(Path(p).resolve() for p in sys.argv[1:4])
installed=len(sys.argv)==5
selected_feed=Path(sys.argv[4]).resolve() if installed else out/'feed'
assert not check.exists(), check
check.mkdir()
here = Path(__file__).resolve().parent
base = subprocess.check_output(['cygpath', '-am', str(root)], text=True).strip()
def native(p):
    p=p.resolve()
    if p.is_relative_to(root):return base+'/'+p.relative_to(root).as_posix()
    return subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
source=out/'roslyn-source'
for suffix, folder in [('compiler', source / 'src/Compilers/VisualBasic/Portable'), ('workspaces', source / 'src/Workspaces/VisualBasic/Portable')]:
    (check / f'api-{suffix}.txt').write_text('\n'.join((folder / name).read_text(encoding='utf-8-sig') for name in ['PublicAPI.Shipped.txt', 'PublicAPI.Unshipped.txt']) + '\n')
config=E.Element('configuration');sources=E.SubElement(config,'packageSources');E.SubElement(sources,'clear')
for i,feed in enumerate([selected_feed,Path('/clang64/lib/dotnet/library-packs')]):E.SubElement(sources,'add',key='source'+str(i),value=native(feed))
E.ElementTree(config).write(check/'NuGet.config',encoding='utf-8',xml_declaration=True)
tree = E.Element('Project', Sdk='Microsoft.NET.Sdk')
pg = E.SubElement(tree, 'PropertyGroup')
for k, v in dict(TargetFramework='net8.0', OutputType='Exe', UseAppHost='false', EnableDefaultItems='false', EnableNETAnalyzers='false', NuGetAudit='false', LangVersion='preview', Nullable='disable', CscToolPath=native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')), CscToolExe='csc50.cmd').items():
    E.SubElement(pg, k).text = v
items = E.SubElement(tree, 'ItemGroup')
for path in sorted((here / 'inputs').glob('*.cs')):
    E.SubElement(items, 'Compile', Include=native(path))
for name in ['Microsoft.CodeAnalysis']:
    E.SubElement(items, 'PackageReference', Include=name, Version='[4.14.0]')
E.ElementTree(tree).write(check / 'Check.csproj', encoding='utf-8', xml_declaration=True)
env = dict(os.environ, DOTNET_CLI_HOME=native(check / 'cli-home'), NUGET_PACKAGES=native(check / 'cache'), DOTNET_CLI_TELEMETRY_OPTOUT='1', MSBuildEnableWorkloadResolver='false')
dotnet = '/clang64/lib/dotnet/dotnet.exe'
with (check / 'build.log').open('w') as log:
    subprocess.run([dotnet, 'build', native(check / 'Check.csproj'), '-c', 'Release', '--configfile', native(check/'NuGet.config'), '-p:UseSharedCompilation=false', '-v:minimal'], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
refs = subprocess.check_output(['cygpath', '-am', '/clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0'], text=True).strip()
command = [dotnet, native(check / 'bin/Release/net8.0/Check.dll'), refs, native(out / 'compiler/localization.json'), native(out / 'workspaces/localization.json'), native(out / 'workspaces/source-items.json'), native(out / 'compiler/source-items.json'), native(check / 'api-compiler.txt'), native(check / 'api-workspaces.txt'), native(source / 'src/Compilers/VisualBasic/Portable/Symbols/EmbeddedSymbols')]
with (check / 'run.log').open('w') as log:
    result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
(check / 'run.exit').write_text(str(result.returncode) + '\n')
assert result.returncode == 0, (result.returncode, check / 'run.log')
(check / 'results.json').write_text(json.dumps(dict(command=command, exit_code=0,formal_pacman_installed=installed,full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS fresh VB4.14 compiler and Workspaces source-feed consumer')
