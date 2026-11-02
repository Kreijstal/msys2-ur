"""Compile the original 13 XLF translations as signed NS2 satellite assemblies."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E

build, out = (Path(p).resolve() for p in sys.argv[1:])
out.mkdir()
source = build / 'snapshot/source'
records = json.loads((build / 'results.json').read_text())['projects']
prefix = Path(subprocess.check_output(['cygpath', '-am', '/clang64'], text=True).strip())
host8 = prefix / 'lib/dotnet/dotnet.exe'
host10 = prefix / 'lib/dotnet10/dotnet.exe'
compiler = prefix / 'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
refs = sorted((prefix / 'lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll'))
assert len(refs) == 113
native = lambda p: Path(p).resolve().as_posix()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
ns = {'x': 'urn:oasis:names:tc:xliff:document:1.2'}
project = E.Element('Project')
E.SubElement(project, 'UsingTask', TaskName='GenerateResource', AssemblyFile=native(host8.parent / 'sdk/8.0.131/Microsoft.Build.Tasks.Core.dll'))
target = E.SubElement(project, 'Target', Name='Generate')
models, jobs, inputs, commands = [], [], {}, []
for entry in records.values():
    for relative in entry['resource_files']:
        resx = source / relative
        name = entry['assembly']
        logical = 'Microsoft.CodeAnalysis.PublicApiAnalyzers.' + resx.stem
        values = {n.get('name'): (n.findtext('value') or '') for n in E.parse(resx).findall('data')}
        models.append(dict(assembly=name, culture='', resource=logical, strings={k:v.replace('\n',os.linesep) for k,v in values.items()}))
        for xlf in sorted((resx.parent / 'xlf').glob(resx.stem + '.*.xlf')):
            tree = E.parse(xlf)
            culture = tree.find('x:file', ns).get('target-language')
            translated = dict(values)
            for item in tree.findall('.//x:trans-unit', ns):
                text = item.find('x:target', ns)
                if text is not None and item.get('id') in translated:
                    translated[item.get('id')] = ''.join(text.itertext())
            inputs[xlf.relative_to(source).as_posix()] = sha(xlf)
            folder = out / culture
            folder.mkdir()
            localized = E.parse(resx)
            for item in localized.findall('data'):
                item.find('value').text = translated[item.get('name')]
            local_file = folder / 'Strings.resx'
            localized.write(local_file, encoding='utf-8', xml_declaration=True)
            E.SubElement(target, 'GenerateResource', Sources=native(local_file), OutputResources=native(local_file.with_suffix('.resources')), ExecuteAsTool='false')
            models.append(dict(assembly=name, culture=culture, resource=logical, strings={k:v.replace('\n',os.linesep) for k,v in translated.items()}))
            jobs.append((name, culture, logical, folder))
E.ElementTree(project).write(out / 'Resources.proj', encoding='utf-8', xml_declaration=True)
def run(label, command, root):
    with (out / (label + '.log')).open('w', encoding='utf-8') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=dict(os.environ, DOTNET_ROOT=native(root), DOTNET_ROOT_X64=native(root)), timeout=180)
    commands.append(dict(command=[str(p) for p in command], exit_code=result.returncode))
    assert result.returncode == 0, label
run('resources', [host8, 'msbuild', out / 'Resources.proj', '-t:Generate', '-nologo', '-v:minimal'], host8.parent)
satellites = {}
for name, culture, logical, folder in jobs:
    info = folder / 'AssemblyInfo.cs'
    info.write_text('[assembly:System.Reflection.AssemblyVersion("3.3.8.6701")]\n[assembly:System.Reflection.AssemblyFileVersion("3.3.8.6701")]\n[assembly:System.Reflection.AssemblyCulture(' + json.dumps(culture) + ')]\n')
    dest = build / 'bin' / culture / (name + '.resources.dll')
    dest.parent.mkdir()
    args = ['/nostdlib+', '/target:library', '/deterministic+', '/publicsign+', '/keyfile:"' + native(build / 'public.snk') + '"', '/out:"' + native(dest) + '"', '/resource:"' + native(folder / 'Strings.resources') + '",' + logical + '.' + culture + '.resources']
    args += ['/reference:"' + native(p) + '"' for p in refs] + ['"' + native(info) + '"']
    rsp = folder / 'compile.rsp'
    rsp.write_text('\n'.join(args) + '\n')
    run(culture, [host10, compiler, '-noconfig', '@' + native(rsp)], host10.parent)
    satellites[dest.relative_to(build / 'bin').as_posix()] = sha(dest)
assert len(satellites) == 13
(out / 'expected.json').write_text(json.dumps(models, ensure_ascii=False) + '\n')
(out / 'results.json').write_text(json.dumps(dict(commands=commands, original_xlf_sha256=inputs, satellite_sha256=satellites, localized_resource_sets=len(jobs), full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS', len(satellites), 'original XLF satellites')
