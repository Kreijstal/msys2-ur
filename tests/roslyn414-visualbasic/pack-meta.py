"""Retain both original dependencies of the Roslyn all-in-one meta package."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E

root, out = (Path(p).resolve() for p in sys.argv[1:])
source = root / 'roslyn414-1/roslyn-source'
original = source / 'src/NuGet/Microsoft.CodeAnalysis.Package/Microsoft.CodeAnalysis.Package.csproj'
upstream = E.parse(original)
refs = [Path(p.get('Include').replace('\\', '/')).stem for p in upstream.iter('ProjectReference')]
assert refs == ['Microsoft.CodeAnalysis.CSharp.Workspaces', 'Microsoft.CodeAnalysis.VisualBasic.Workspaces'], refs
assert upstream.findtext('.//IncludeBuildOutput') == 'false'
assert 'netstandard2.0' in upstream.findtext('.//TargetFrameworks').split(';')
folder = out / 'meta'
folder.mkdir()
base = subprocess.check_output(['cygpath', '-am', str(root)], text=True).strip()
def native(p):
    return base + '/' + p.resolve().relative_to(root).as_posix()
tree = E.Element('Project', Sdk='Microsoft.NET.Sdk')
pg = E.SubElement(tree, 'PropertyGroup')
for k, v in dict(TargetFramework='netstandard2.0', PackageId='Microsoft.CodeAnalysis', Version='4.14.0', IncludeBuildOutput='false', EnableDefaultItems='false', EnableNETAnalyzers='false', NuGetAudit='false', PackageLicenseExpression='MIT', RepositoryUrl='https://github.com/dotnet/roslyn', RepositoryCommit='8edf7bcd4f1594c3d68a6a567469f41dbd33dd1b', NoWarn='NU5128', Description=upstream.findtext('.//PackageDescription').strip()).items():
    E.SubElement(pg, k).text = v
items = E.SubElement(tree, 'ItemGroup')
for name in refs:
    E.SubElement(items, 'PackageReference', Include=name, Version='[4.14.0]')
for name in ['License.txt', 'THIRD-PARTY-NOTICES.txt']:
    E.SubElement(items, 'None', Include=native(source / name), Pack='true', PackagePath='/')
E.indent(tree)
E.ElementTree(tree).write(folder / 'Build.csproj', encoding='utf-8', xml_declaration=True)
env = dict(os.environ, DOTNET_CLI_HOME=native(out / 'cli-home'), NUGET_PACKAGES=native(out / 'cache'), DOTNET_CLI_TELEMETRY_OPTOUT='1', MSBuildEnableWorkloadResolver='false')
command = ['/clang64/lib/dotnet/dotnet.exe', 'pack', native(folder / 'Build.csproj'), '-c', 'Release', '--configfile', native(out / 'NuGet.config'), '-o', native(out / 'feed'), '-p:UseSharedCompilation=false', '-v:minimal']
with (folder / 'build.log').open('w') as log:
    subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
(folder / 'source-inputs.json').write_text(json.dumps(dict(original_project=str(original.relative_to(source)), original_project_sha256=hashlib.sha256(original.read_bytes()).hexdigest(), dependencies={name: '4.14.0' for name in refs}, command=command, formal_pacman_installed=False), indent=2) + '\n')
print('PASS original Microsoft.CodeAnalysis4.14 meta package with both language Workspaces dependencies')
