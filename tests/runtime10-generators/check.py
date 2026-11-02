"""Run original shipping generators against source-built .NET10/.NET8 contracts."""
from pathlib import Path
import os
import subprocess
import sys
import xml.etree.ElementTree as E

root, out, check = (Path(p).resolve() for p in sys.argv[1:4])
json_runtime = Path(sys.argv[4]).resolve() if len(sys.argv) == 5 else root / 'json10-net8-1'
assert not check.exists(), check
check.mkdir()
here = Path(__file__).resolve().parent
base = subprocess.check_output(['cygpath', '-am', str(root)], text=True).strip()
def native(p):
    return base + '/' + p.resolve().relative_to(root).as_posix()
tree = E.Element('Project', Sdk='Microsoft.NET.Sdk')
pg = E.SubElement(tree, 'PropertyGroup')
for k, v in dict(TargetFramework='net8.0', AssemblyName='Check', OutputType='Exe', UseAppHost='false', EnableDefaultItems='false', EnableNETAnalyzers='false', NuGetAudit='false', Nullable='disable', LangVersion='preview', CscToolPath=native(root / 'cdac-bootstrap5/compiler'), CscToolExe='csc50.cmd').items():
    E.SubElement(pg, k).text = v
items = E.SubElement(tree, 'ItemGroup')
E.SubElement(items, 'Compile', Include=native(here / 'inputs/Check.cs'))
E.SubElement(items, 'PackageReference', Include='Microsoft.CodeAnalysis.CSharp.Workspaces', Version='[4.14.0]')
E.ElementTree(tree).write(check / 'Build.csproj', encoding='utf-8', xml_declaration=True)
env = dict(os.environ, DOTNET_CLI_HOME=native(check / 'cli-home'), NUGET_PACKAGES=native(check / 'cache'), DOTNET_CLI_TELEMETRY_OPTOUT='1', MSBuildEnableWorkloadResolver='false')
dotnet = '/clang64/lib/dotnet/dotnet.exe'
with (check / 'build.log').open('w') as log:
    subprocess.run([dotnet, 'build', native(check / 'Build.csproj'), '-c', 'Release', '--configfile', native(out / 'NuGet.config'), '-p:UseSharedCompilation=false', '-v:minimal'], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
reference8 = subprocess.check_output(['cygpath', '-am', '/clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0'], text=True).strip()
command = [dotnet, native(check / 'bin/Release/net8.0/Check.dll'), native(out), base, native(root / 'reference10-2/ref/net10.0'), reference8, native(check), native(json_runtime)]
with (check / 'run.log').open('w') as log:
    result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=300)
(check / 'run.exit').write_text(str(result.returncode) + '\n')
assert result.returncode == 0, (result.returncode, check / 'run.log')
print('PASS original six-generator .NET10 netstandard2.0 bundle runtime consumer')
