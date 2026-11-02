"""Build the original NETStandard.Library2.0.3 netstandard2.0 reference assets."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

root, out = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(), out
out.mkdir(parents=True)
here = Path(__file__).resolve().parent
commit = '18a36291e48808fa7ef2d00a764ceb1ec95645a5'
archive = root / 'standard-18a36291.tar.gz'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == '754ee66a33122c6c5c45fe75d060f9131c6b16a23af315c8c063a54fbc911e7c'
with tarfile.open(archive) as tar:
    assert tar.pax_headers['comment'] == commit
    tar.extractall(out, filter='data')
source = out / ('standard-' + commit)
removed = []
for path in source.rglob('*'):
    if path.is_file() and path.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.obj','.lib','.resources'}:
        removed.append(dict(path=path.relative_to(source).as_posix(), sha256=sha(path)))
        path.unlink()
(out / 'removed-binaries.json').write_text(json.dumps(removed, indent=2)+'\n')
ns = {'m':'http://schemas.microsoft.com/developer/msbuild/2003'}
native_root = subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
def native(p): return native_root+'/'+p.resolve().relative_to(root).as_posix()
keys = {}
for name in ['Open','ECMA','MSFT','SilverlightExtension']:
    p = out/(name+'.pubkey')
    p.write_bytes(bytes.fromhex((here/'inputs'/(name+'.pubkey.hex')).read_text()))
    keys[name] = p
projects = [source/'netstandard/ref/netstandard.csproj',
            *sorted((source/'platforms/extensions').glob('*.csproj')),
            *sorted((source/'netstandard/pkg/shims').rglob('*.csproj'))]
assert len(projects) == 117
records = {}
for project in projects:
    tree = E.parse(project)
    value = lambda name: tree.findtext('.//m:'+name, namespaces=ns)
    name = value('AssemblyName') or project.stem
    assert name not in records, name
    files = [(project.parent/e.get('Include').replace('\\','/')).resolve()
             for e in tree.findall('.//m:Compile',ns)]
    deps = [(project.parent/e.get('Include').replace('\\','/')).resolve()
            for e in tree.findall('.//m:ProjectReference',ns)]
    assert all(p.is_file() for p in files+deps), project
    assert all('$(' not in str(p) for p in files+deps)
    records[name] = dict(project=project.relative_to(source).as_posix(), project_sha256=sha(project),
                         assembly_version=value('AssemblyVersion'), key=value('AssemblyKey') or 'Open',
                         source_cs={p.relative_to(source).as_posix():sha(p) for p in files},
                         dependency_projects=[p.relative_to(source).as_posix() for p in deps],
                         package_asset='platforms/extensions/' not in project.relative_to(source).as_posix())
project_names = {r['project']:n for n,r in records.items()}
for r in records.values(): r['dependencies']=[project_names[p] for p in r['dependency_projects']]
order = []
def visit(name):
    if name in order: return
    for dep in records[name]['dependencies']: visit(dep)
    order.append(name)
for name in records: visit(name)
dotnet = '/clang64/lib/dotnet/dotnet.exe'
compiler = root/'cdac-bootstrap5/compiler/CompilerHost.dll'
(out/'ref').mkdir()
(out/'extensions').mkdir()
def product(name): return out/('ref' if records[name]['package_asset'] else 'extensions')/(name+'.dll')
for name in order:
    r = records[name]
    folder = out/'build'/name
    folder.mkdir(parents=True)
    info = folder/'AssemblyInfo.cs'
    info.write_text('[assembly:System.Reflection.AssemblyVersion('+json.dumps(r['assembly_version'])+')]\n'
                    '[assembly:System.Reflection.AssemblyFileVersion("2.0.3.0")]\n'
                    '[assembly:System.Reflection.AssemblyInformationalVersion("2.0.3+'+commit+'")]\n'
                    '[assembly:System.Reflection.AssemblyMetadata(".NETFrameworkAssembly", "")]\n')
    closure = set()
    def dependencies(n):
        for dep in records[n]['dependencies']:
            if dep not in closure: closure.add(dep); dependencies(dep)
    dependencies(name)
    args = ['/nostdlib+', '/target:library', '/refonly', '/unsafe+', '/deterministic+',
            '/langversion:7.3', '/runtimemetadataversion:v4.0.30319', '/nowarn:0618;0619;0809',
            '/publicsign+', '/keyfile:"'+native(keys[r['key']])+'"', '/out:"'+native(product(name))+'"']
    args += ['/reference:"'+native(product(dep))+'"' for dep in order if dep in closure]
    args += ['"'+native(source/p)+'"' for p in r['source_cs']]+['"'+native(info)+'"']
    rsp = folder/'compile.rsp'
    rsp.write_text('\n'.join(args)+'\n')
    command = [dotnet, native(compiler), '-noconfig', '@'+native(rsp)]
    with (folder/'compile.log').open('w') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    r.update(command=command, exit_code=result.returncode)
    (out/'build-results.json').write_text(json.dumps(records,indent=2)+'\n')
    assert result.returncode == 0, (name,folder/'compile.log')
    r['output_sha256'] = sha(product(name))
    print('PASS source reference', name, flush=True)
(out/'build-results.json').write_text(json.dumps(records,indent=2)+'\n')
print('PASS 117 original source reference assemblies; 113 package assets', flush=True)
