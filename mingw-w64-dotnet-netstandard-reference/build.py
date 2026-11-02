"""Build the original NETStandard.Library2.0.3 netstandard2.0 reference assets."""
from pathlib import Path
import hashlib
import datetime
import json
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

archive, out = (Path(p).resolve() for p in sys.argv[1:3])
assert not out.exists(), out
out.mkdir(parents=True)
here = Path(__file__).resolve().parent
provenance = json.loads((here/'inputs/key-provenance.json').read_text())
assert hashlib.sha256((here/'inputs/buildtools-sign.targets').read_bytes()).hexdigest() == provenance['sign_targets_sha256']
silverlight = bytes.fromhex((here/'inputs/SilverlightExtension.pubkey.hex').read_text())
assert hashlib.sha256(silverlight).hexdigest() == provenance['key_sha256']
assert hashlib.sha1(silverlight).digest()[-8:][::-1].hex() == provenance['public_key_token']
version_policy = json.loads((here/'inputs/version-policy.json').read_text())
common_policy = E.parse(here/'inputs/buildtools-Build.Common.targets').getroot()
assert version_policy['cls_compliant_default'] is True
assert any(e.tag.endswith('CLSCompliant') and e.text=='true' and e.get('Condition')=="'$(CLSCompliant)'==''" for e in common_policy.iter())
tools_archive = Path(sys.argv[3]).resolve()
assert hashlib.sha256(tools_archive.read_bytes()).hexdigest() == version_policy['archive_sha256']
with tarfile.open(tools_archive) as tools:
    assert tools.pax_headers['comment'] == version_policy['commit']
    found = set()
    for member in tools:
        name = member.name.partition('/')[2]
        if name in version_policy['inputs']:
            item = version_policy['inputs'][name]
            data = tools.extractfile(member).read()
            assert hashlib.sha256(data).hexdigest() == item['sha256']
            assert (here/'inputs'/item['local_file']).read_bytes() == data
            found.add(name)
    assert found == set(version_policy['inputs'])
commit = '18a36291e48808fa7ef2d00a764ceb1ec95645a5'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == '754ee66a33122c6c5c45fe75d060f9131c6b16a23af315c8c063a54fbc911e7c'
with tarfile.open(archive) as tar:
    assert tar.pax_headers['comment'] == commit
    source_date = datetime.datetime.fromtimestamp(tar.getmembers()[0].mtime, datetime.timezone.utc).date()
    assert str(source_date) == version_policy['source_seed_date']
    months = (source_date.year-1996)*12 + source_date.month-4
    assert int(f'{months:03}{source_date.day:02}') == version_policy['source_date_build_number']
    tar.extractall(out, filter='data')
source = out / ('standard-' + commit)
removed = []
for path in source.rglob('*'):
    if path.is_file() and path.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.obj','.lib','.resources'}:
        removed.append(dict(path=path.relative_to(source).as_posix(), sha256=sha(path)))
        path.unlink()
(out / 'removed-binaries.json').write_text(json.dumps(removed, indent=2)+'\n')
ns = {'m':'http://schemas.microsoft.com/developer/msbuild/2003'}
shim_policy = E.parse(source/'netstandard/pkg/shims/dir.targets')
assert shim_policy.findtext('.//m:MajorVersion', namespaces=ns) == '4'
assert shim_policy.findtext('.//m:MinorVersion', namespaces=ns) == '6'
assert shim_policy.find('.//m:Target[@Name="ClearReferenceAssemblyBits"]//m:AssemblyInfoLines[@Remove="@(AssemblyInfoLines)"]', ns) is not None
native_root = subprocess.check_output(['cygpath','-am',str(out)],text=True).strip()
def native(p):
    p=p.resolve()
    if p.is_relative_to(out):return native_root+'/'+p.relative_to(out).as_posix()
    return subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
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
    shim = 'netstandard/pkg/shims/' in project.relative_to(source).as_posix()
    records[name]['reference_only'] = not shim
    records[name]['file_version'] = version_policy['facade_file_version'] if shim else '2.0.3.0'
    records[name]['framework_assembly_metadata'] = bool(tree.findall('.//m:AssemblyMetadata', ns))
    records[name]['cls_compliant'] = True
project_names = {r['project']:n for n,r in records.items()}
for r in records.values(): r['dependencies']=[project_names[p] for p in r['dependency_projects']]
order = []
def visit(name):
    if name in order: return
    for dep in records[name]['dependencies']: visit(dep)
    order.append(name)
for name in records: visit(name)
dotnet = '/clang64/lib/dotnet/dotnet.exe'
compiler = Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap/CompilerHost.dll')
owner = subprocess.check_output(['pacman', '-Qo', str(compiler)], text=True).strip()
assert 'mingw-w64-clang-x86_64-dotnet-compiler5-bootstrap' in owner
(out/'tool-inputs.json').write_text(json.dumps(dict(compiler_owner=owner, compiler_host_sha256=sha(compiler), key_provenance=provenance, version_policy=version_policy), indent=2)+'\n')
(out/'ref').mkdir()
(out/'extensions').mkdir()
def product(name): return out/('ref' if records[name]['package_asset'] else 'extensions')/(name+'.dll')
for name in order:
    r = records[name]
    folder = out/'build'/name
    folder.mkdir(parents=True)
    info = folder/'AssemblyInfo.cs'
    info.write_text('[assembly:System.Reflection.AssemblyVersion('+json.dumps(r['assembly_version'])+')]\n'
                    '[assembly:System.CLSCompliant(true)]\n'
                    '[assembly:System.Reflection.AssemblyFileVersion('+json.dumps(r['file_version'])+')]\n'
                    '[assembly:System.Reflection.AssemblyInformationalVersion("2.0.3+'+commit+'")]\n'
                    + ('[assembly:System.Reflection.AssemblyMetadata(".NETFrameworkAssembly", "")]\n' if r['framework_assembly_metadata'] else ''))
    closure = set()
    def dependencies(n):
        for dep in records[n]['dependencies']:
            if dep not in closure: closure.add(dep); dependencies(dep)
    dependencies(name)
    args = ['/nostdlib+', '/target:library', '/unsafe+', '/deterministic+',
            '/langversion:7.3', '/runtimemetadataversion:v4.0.30319', '/nowarn:0618;0619;0809',
            '/publicsign+', '/keyfile:"'+native(keys[r['key']])+'"', '/out:"'+native(product(name))+'"']
    if r['reference_only']: args.append('/refonly')
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
subprocess.run(['/usr/bin/python3', str(here/'pack.py'), str(out)], check=True)
