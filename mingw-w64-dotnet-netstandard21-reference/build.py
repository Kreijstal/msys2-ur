"""Build the original v2.1.0 Standard reference graph with installed source tools."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

archive, arcade, out = map(lambda p: Path(p).resolve(), sys.argv[1:])
assert not out.exists(), out
out.mkdir(parents=True)
here = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
commit = 'a5b5f2e1e369972c8ff1e2183979fab6099f52ef'
assert sha(archive) == 'e681d3377e3ffa79cb97685e3fa3966a645017fa35ed7f3aef6b3566547fb794'
provenance = json.loads((here/'inputs/arcade-provenance.json').read_text())
assert sha(arcade) == provenance['archive_sha256']
with tarfile.open(arcade) as t:
    assert t.pax_headers['comment'] == provenance['commit']
    seen = set()
    for m in t:
        name = m.name.partition('/')[2]
        if name in provenance['inputs']:
            entry = provenance['inputs'][name]
            data = t.extractfile(m).read()
            assert hashlib.sha256(data).hexdigest() == entry['sha256']
            assert data == (here/'inputs'/entry['local']).read_bytes()
            seen.add(name)
    assert seen == set(provenance['inputs'])
with tarfile.open(archive) as t:
    assert t.pax_headers['comment'] == commit
    seed = datetime.datetime.fromtimestamp(t.getmembers()[0].mtime, datetime.timezone.utc)
    t.extractall(out, filter='data')
source = out/('standard-'+commit)
removed = []
for p in source.rglob('*'):
    if p.is_file() and p.suffix.lower() in {'.dll','.exe','.nupkg','.pdb','.obj','.lib','.resources','.snk'}:
        removed.append(dict(path=p.relative_to(source).as_posix(), sha256=sha(p)))
        p.unlink()
ns = {'m':'http://schemas.microsoft.com/developer/msbuild/2003'}
assert E.parse(source/'Directory.Build.targets').findtext('.//m:CLSCompliant',namespaces=ns) == 'true'
assert E.parse(source/'eng/Version.Details.xml').findtext('.//Dependency[@Name="Microsoft.DotNet.Arcade.Sdk"]/Sha') == provenance['commit']
native_root = subprocess.check_output(['cygpath','-am',str(out)],text=True).strip()
def native(p):
    p = p.resolve()
    if p.is_relative_to(out): return native_root+'/'+p.relative_to(out).as_posix()
    return subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
keys = {}
for name in ['Open','ECMA','Microsoft','MicrosoftShared']:
    data = bytes.fromhex(E.parse(here/'inputs/arcade-StrongName.props').findtext('.//'+name+'PublicKey'))
    p = out/(name+'.pubkey');p.write_bytes(data);keys[name] = p
projects = [source/'src/netstandard/ref/netstandard.csproj',
            *sorted((source/'src/platforms/extensions').glob('*.csproj')),
            *sorted((source/'src/netstandard/pkg/shims').rglob('*.csproj'))]
assert len(projects) == 125
records = {}
for p in projects:
    tree = E.parse(p);value = lambda n:tree.findtext('.//'+n)
    name = value('AssemblyName') or p.stem
    files = [(p.parent/e.get('Include').replace('\\','/')).resolve() for e in tree.findall('.//Compile')]
    deps = [(p.parent/e.get('Include').replace('\\','/')).resolve() for e in tree.findall('.//ProjectReference')]
    assert all(f.is_file() for f in files+deps)
    core = name == 'netstandard'
    # Original Version.props/CalculateAssemblyAndFileVersions with source UTC date, revision 1.
    major,minor = (1,1) if core else (4,7)
    fv = f'{major}.{minor*100}.{seed.year%100}.{seed.month*5000+seed.day*100+1}'
    package_asset = '/platforms/extensions/' not in p.as_posix()
    records[name] = dict(project=p.relative_to(source).as_posix(),project_sha256=sha(p),
        source_cs={f.relative_to(source).as_posix():sha(f) for f in files},
        dependency_projects=[f.relative_to(source).as_posix() for f in deps],
        assembly_version=value('AssemblyVersion'),key=value('StrongNameKeyId') or 'Open',
        reference_only=package_asset,package_asset=package_asset,framework_assembly_metadata=core,
        cls_compliant=True,file_version=fv)
names = {r['project']:n for n,r in records.items()}
for r in records.values():r['dependencies']=[names[p] for p in r['dependency_projects']]
order = []
def visit(name):
    if name in order:return
    for dep in records[name]['dependencies']:visit(dep)
    order.append(name)
for name in records:visit(name)
dotnet = '/clang64/lib/dotnet/dotnet.exe'
compiler = Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap/CompilerHost.dll')
owner = subprocess.check_output(['pacman','-Qo',str(compiler)],text=True).strip()
assert 'dotnet-compiler5-bootstrap' in owner
(out/'tool-inputs.json').write_text(json.dumps(dict(compiler_owner=owner,compiler_sha256=sha(compiler),arcade=provenance,source_date=seed.isoformat()),indent=2)+'\n')
(out/'removed-binaries.json').write_text(json.dumps(removed,indent=2)+'\n')
for name in ['ref','extensions']:(out/name).mkdir()
def product(name):return out/('ref' if records[name]['package_asset'] else 'extensions')/(name+'.dll')
for name in order:
    r=records[name];folder=out/'build'/name;folder.mkdir(parents=True)
    info=folder/'AssemblyInfo.cs'
    attrs = [('System.Reflection.AssemblyVersion',r['assembly_version']),
             ('System.Reflection.AssemblyFileVersion',r['file_version']),
             ('System.Reflection.AssemblyInformationalVersion','2.1.0+'+commit),
             ('System.Reflection.AssemblyDefaultAlias',name),('System.Reflection.AssemblyDescription',name),
             ('System.Reflection.AssemblyProduct','Microsoft® .NET Framework')]
    info.write_text(''.join('[assembly:'+a+'('+json.dumps(v)+')]\n' for a,v in attrs)+
        '[assembly:System.CLSCompliant(true)]\n'+
        ('[assembly:System.Reflection.AssemblyMetadata(".NETFrameworkAssembly", "")]\n' if name=='netstandard' else '')+
        ('[assembly:System.Reflection.AssemblyFlags((System.Reflection.AssemblyNameFlags)0x70)]\n' if r['reference_only'] else ''))
    closure=set()
    def dependencies(n):
        for dep in records[n]['dependencies']:
            if dep not in closure:closure.add(dep);dependencies(dep)
    dependencies(name)
    args=['/nostdlib+','/target:library','/unsafe+','/deterministic+','/optimize+','/define:TRACE',
          '/langversion:8.0','/runtimemetadataversion:v4.0.30319','/nowarn:0618;0619;0809;0169;0649',
          '/publicsign+','/keyfile:"'+native(keys[r['key']])+'"','/out:"'+native(product(name))+'"']
    if r['reference_only']:args += ['/refonly']
    args += ['/reference:"'+native(product(d))+'"' for d in order if d in closure]
    args += ['"'+native(source/f)+'"' for f in r['source_cs']]+['"'+native(info)+'"']
    rsp=folder/'compile.rsp';rsp.write_text('\n'.join(args)+'\n')
    command=[dotnet,native(compiler),'-noconfig','@'+native(rsp)]
    with (folder/'compile.log').open('w') as log:result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
    r.update(command=command,exit_code=result.returncode)
    (out/'build-results.json').write_text(json.dumps(records,indent=2)+'\n')
    assert result.returncode==0,(name,folder/'compile.log')
    r['output_sha256']=sha(product(name))
    print('PASS source Standard2.1 reference',name,flush=True)
(out/'build-results.json').write_text(json.dumps(records,indent=2)+'\n')
assert len(list((out/'ref').glob('*.dll')))==121
print('PASS 125 original source assemblies; 121 Standard2.1 reference assets',flush=True)
