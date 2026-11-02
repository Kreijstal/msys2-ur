"""Exercise the package compiler through actual SDK build, Unicode RSP and errors."""
from pathlib import Path
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E

prepared, out = (Path(p).resolve() for p in sys.argv[1:3])
compiler = Path(sys.argv[3]).resolve() if len(sys.argv) == 4 else prepared / 'compiler'
assert not out.exists(), out
out.mkdir()
here = Path(__file__).resolve().parent
def native(p):
    return subprocess.check_output(['cygpath', '-am', str(p)], text=True).strip()
env = dict(os.environ, DOTNET_CLI_HOME=native(out / 'cli-home'), NUGET_PACKAGES=native(out / 'cache'), DOTNET_CLI_TELEMETRY_OPTOUT='1', MSBuildEnableWorkloadResolver='false')
dotnet = '/clang64/lib/dotnet/dotnet.exe'
wrapper = 'csc50.cmd' if len(sys.argv) == 4 else 'csc50-build.cmd'
version = subprocess.check_output([dotnet, native(compiler / 'CompilerHost.dll'), '-version'], env=env, text=True).strip()
assert version.startswith('5.0.0'), version
(out / 'version.log').write_text(version + '\n')
for name in ['generator', 'consumer']:
    folder = out / name
    folder.mkdir()
    tree = E.Element('Project', Sdk='Microsoft.NET.Sdk')
    pg = E.SubElement(tree, 'PropertyGroup')
    for k, v in dict(TargetFramework='net8.0', AssemblyName='OwnedGenerator' if name == 'generator' else 'Probe', OutputType='Library' if name == 'generator' else 'Exe', UseAppHost='false', EnableDefaultItems='false', EnableNETAnalyzers='false', NuGetAudit='false', LangVersion='preview', Nullable='enable', CscToolPath=native(compiler), CscToolExe=wrapper, UseSharedCompilation='false').items():
        E.SubElement(pg, k).text = v
    items = E.SubElement(tree, 'ItemGroup')
    E.SubElement(items, 'Compile', Include=native(here / 'inputs' / ('Generator.cs' if name == 'generator' else 'Probe.cs')))
    if name == 'generator':
        for ident in ['Microsoft.CodeAnalysis', 'Microsoft.CodeAnalysis.CSharp', 'System.Collections.Immutable', 'System.Reflection.Metadata']:
            E.SubElement(E.SubElement(items, 'Reference', Include=ident), 'HintPath').text = native(compiler / (ident + '.dll'))
    else:
        E.SubElement(items, 'ProjectReference', Include='../generator/Build.csproj', OutputItemType='Analyzer', ReferenceOutputAssembly='false')
        E.SubElement(pg, 'EmitCompilerGeneratedFiles').text = 'true'
        E.SubElement(pg, 'CompilerGeneratedFilesOutputPath').text = 'generated'
    E.indent(tree)
    E.ElementTree(tree).write(folder / 'Build.csproj', encoding='utf-8', xml_declaration=True)
config = out / 'NuGet.config'
config.write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
with (out / 'build.log').open('w') as log:
    subprocess.run([dotnet, 'build', native(out / 'consumer/Build.csproj'), '-c', 'Release', '--configfile', native(config), '-p:UseSharedCompilation=false', '-v:minimal'], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
text = (out / 'build.log').read_text()
assert 'C5PKG001' in text
assert not any(c in text for c in ['CS8032', 'CS8784', 'CS8785', 'AD0001'])
with (out / 'run.log').open('w') as log:
    subprocess.run([dotnet, native(out / 'consumer/bin/Release/net8.0/Probe.dll')], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
source = out / 'owned π space.cs'
source.write_text('public static class UnicodeOwned {public static int Value()=>42;}\n')
refs = Path('/clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0')
rsp = out / 'owned π response.rsp'
args = ['-nologo', '-nostdlib+', '-target:library', '-langversion:preview', '-out:"' + native(out / 'unicode-owned.dll') + '"']
args += ['-r:"' + native(p) + '"' for p in sorted(refs.glob('*.dll'))]
args.append('"' + native(source) + '"')
rsp.write_text('\n'.join(args) + '\n', encoding='utf-8')
subprocess.run([dotnet, native(compiler / 'CompilerHost.dll'), '-noconfig', '@' + native(rsp)], env=env, check=True)
assert (out / 'unicode-owned.dll').is_file()
broken = out / 'broken.cs'
broken.write_text('public class {\n')
with (out / 'negative.log').open('w') as log:
    result = subprocess.run([dotnet, native(compiler / 'CompilerHost.dll'), '-noconfig', '@' + native(rsp), native(broken)], env=env, stdout=log, stderr=subprocess.STDOUT)
assert result.returncode == 1
(out / 'results.json').write_text(json.dumps(dict(version=version, csharp14_compilation_and_execution=True, original_analyzer_callback=True, source_runtime9_in_compiler_generator_context=True, unicode_space_response_file=True, invalid_source_exit_code=1, installed_compiler=bool(len(sys.argv) == 4), full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS source Compiler5 SDK build/generator/analyzer/runtime9/CSharp14/Unicode-RSP/error checks')
