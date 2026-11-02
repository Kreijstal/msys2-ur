"""Check unchanged original projects, compiler inputs, policy and package layout."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

out=Path(sys.argv[1]).resolve();source=out/'source'
record=json.loads((out/'source-inputs.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=subprocess.check_output(['cygpath','-am',str(out)],text=True).strip()
def posix(value):
    value=value.replace('\\','/')
    assert value.lower().startswith(base.lower()+'/'),value
    return out/value[len(base)+1:]
ports=record['source_ports'];assert len(ports)==5
for rel,digest in record['original_file_sha256'].items():
    if rel in ports:
        assert ports[rel]['original_sha256']==digest
        digest=ports[rel]['ported_sha256']
    assert sha(source/rel)==digest,rel
generator=source/'src/PolySharp.SourceGenerators'
obj=generator/'obj/Release/netstandard2.0'
policy=(obj/'recorded-policy.txt').read_text().strip().split('|')
assert policy==['netstandard2.0','13.0','enable','true','strict','1.15.0.0','1.15.0','7','true','embedded'],policy
compiled={posix(line) for line in (obj/'recorded-Compile.txt').read_text().splitlines() if line}
original_cs={source/rel for rel in record['original_file_sha256'] if rel.startswith('src/PolySharp.SourceGenerators/') and rel.endswith('.cs')}
assert len(original_cs)==74 and original_cs.issubset(compiled)
extras=compiled-original_cs
assert len(extras)==3 and all(p.is_relative_to(obj) for p in extras),extras
skip=next(p for p in extras if p.name.endswith('.SkipLocalsInit.g.cs'))
assert '[module: System.Runtime.CompilerServices.SkipLocalsInitAttribute]' in skip.read_text()
resources={posix(line.partition('|')[0]) for line in (obj/'recorded-EmbeddedResource.txt').read_text().splitlines() if line}
assert resources=={p for p in original_cs if p.is_relative_to(generator/'EmbeddedResources')}
assert len(resources)==56 and resources.issubset(compiled)
assets_files=[generator/'obj/project.assets.json',source/'src/PolySharp.Package/obj/project.assets.json']
dependencies=[]
feed=Path('/clang64/lib/dotnet/library-packs')
for path in assets_files:
    assets=json.loads(path.read_text())
    assert not assets.get('logs'),assets.get('logs')
    assert len(assets['packageFolders'])==1
    cache=posix(next(iter(assets['packageFolders'])))
    for name,item in assets['libraries'].items():
        if item['type']!='package':continue
        ident,version=name.split('/');filename=ident.lower()+'.'+version+'.nupkg'
        archive=feed/filename
        assert (cache/item['path']/filename).read_bytes()==archive.read_bytes()
        with zipfile.ZipFile(archive) as z:
            for member in z.namelist():
                if member.endswith(('.dll','.props','.targets')):assert (cache/item['path']/member).read_bytes()==z.read(member)
        dependencies.append(dict(project=str(path.relative_to(source)),package=name,source_archive_sha256=sha(archive)))
    assert 'DotNet.ReproducibleBuilds/1.2.25' in assets['libraries']
    if path==assets_files[0]:assert 'Microsoft.CodeAnalysis.CSharp/4.3.1' in assets['libraries']
archive=out/'feed/PolySharp.1.15.0.nupkg'
with zipfile.ZipFile(archive) as z:
    md=E.fromstring(z.read('PolySharp.nuspec')).find('{*}metadata')
    assert md.findtext('{*}id')=='PolySharp' and md.findtext('{*}version')=='1.15.0'
    assert md.findtext('{*}developmentDependency')=='true'
    assert z.read('analyzers/dotnet/cs/PolySharp.SourceGenerators.dll')==(generator/'bin/Release/netstandard2.0/PolySharp.SourceGenerators.dll').read_bytes()
    assert [n for n in z.namelist() if n.endswith('.dll')]==['analyzers/dotnet/cs/PolySharp.SourceGenerators.dll']
    assert not any(n.startswith(('lib/','ref/')) for n in z.namelist())
    for prefix in ['build/','buildTransitive/']:assert z.read(prefix+'PolySharp.targets')==(generator/'PolySharp.targets').read_bytes()
    for name in ['README.md','icon.png']:assert z.read(name)==(source/'src/PolySharp.Package'/name).read_bytes()
    members={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
result=dict(original_source_files_verified=len(record['original_file_sha256']),production_source_changes=5,source_ports=ports,
    original_CSharp_inputs=74,original_embedded_CSharp_inputs=56,original_SkipLocalsInit_target_executed=True,
    actual_compiler_policy=policy,actual_source_dependency_archives=dependencies,
    source_nupkg_sha256=sha(archive),archive_members=members,
    original_generator_and_package_projects_used=True,full_dependency_goal_complete=False)
(out/'producer-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS original PolySharp source inputs, strict policy, dual compile/resource items, generated module attribute, exact source dependencies and original NuGet layout')
