"""Audit Roslyn source TFMs, pinned source/generated inputs and actual package caches."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

root,out,consumer=(Path(p).resolve() for p in sys.argv[1:])
source=root/'roslyn414-1/roslyn-source'
record=json.loads((out/'source-inputs.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
native_root=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
def posix(p):
    p=p.replace('\\','/').rstrip('/');assert p.lower().startswith(native_root.lower()+'/'),p
    return root/p[len(native_root)+1:]
wanted={};packages={}
for name,item in record['projects'].items():
    assert item['production_cs_changes']==0
    wanted[item['original_project']]=item['original_project_sha256'];wanted.update(item['original_cs']);wanted.update(item['original_resources'])
    language='Core' if name=='Microsoft.CodeAnalysis' else 'CSharp'
    main=source/'src/Compilers'/language/'Portable'
    for file in [main/'PublicAPI.Shipped.txt',main/'PublicAPI.Unshipped.txt',source/'License.txt',source/'THIRD-PARTY-NOTICES.txt']:
        wanted[file.relative_to(source).as_posix()]=sha(file)
    for resx in main.rglob('*.resx'):
        for xlf in (resx.parent/'xlf').glob(resx.stem+'.*.xlf'):wanted[xlf.relative_to(source).as_posix()]=sha(xlf)
    tree=E.parse(out/name/'Build.csproj')
    assert tree.findtext('.//TargetFramework')=='netstandard2.0'
    actual={e.get('Include'):e.get('Version').strip('[]') for e in tree.iter('PackageReference')}
    assert actual==item['resolved_dependencies']
    for ident,minimum in item['original_package_minimums'].items():
        assert tuple(map(int,actual[ident].split('.')))>=tuple(map(int,minimum.split('.')))
    for generated in (out/name).glob('*.Generated.cs'):
        assert generated.read_bytes()==(root/'roslyn414-1'/name/generated.name).read_bytes(),generated
    ident='Microsoft.CodeAnalysis.Common' if language=='Core' else name
    package=out/'feed'/(ident+'.4.14.0.nupkg')
    with zipfile.ZipFile(package) as z:
        spec=E.fromstring(z.read(next(n for n in z.namelist() if n.endswith('.nuspec'))));md=next(e for e in spec if e.tag.endswith('metadata'))
        values={e.tag.rsplit('}',1)[-1]:e.text for e in md};assert values['id']==ident and values['version']=='4.14.0'
        repo=next(e for e in md if e.tag.endswith('repository'));assert repo.get('commit')==record['roslyn_commit']
        deps={e.get('id'):e.get('version').strip('[]') for e in md.iter() if e.tag.endswith('dependency')}
        assert deps==actual,(name,deps,actual)
        assert all(e.get('targetFramework')=='.NETStandard2.0' for e in md.iter() if e.tag.endswith('group'))
        for path in z.namelist():
            if path.startswith('lib/netstandard2.0/') and path.endswith('.dll'):
                relative=path.removeprefix('lib/netstandard2.0/')
                assert (out/name/'bin/Release/netstandard2.0'/relative).read_bytes()==z.read(path),(name,path)
                assert (consumer/'bin/Release/net8.0'/relative).read_bytes()==z.read(path),(name,path)
        for file in ['License.txt','THIRD-PARTY-NOTICES.txt']:assert z.read(file)==(source/file).read_bytes(),(name,file)
        packages[ident]=dict(version='4.14.0',sha256=sha(package),dependencies=deps)
for path,field in [('eng/Versions.props','original_versions_sha256'),('eng/Directory.Packages.props','original_central_packages_sha256')]:wanted[path]=record[field]
generated_inputs=[]
for entry in record['original_generated_sources']:
    file=root/'roslyn414-1/generated'/entry['file'];assert sha(file)==entry['sha256']
    matches=list((source/'src/Compilers/CSharp/Portable/Generated').rglob(entry['file']));assert len(matches)==1
    original=matches[0];assert sha(original)==entry['upstream_sha256']
    wanted[original.relative_to(source).as_posix()]=sha(original);generated_inputs.append(dict(file=entry['file'],sha256=sha(file),upstream_sha256=sha(original)))
archive=root/'roslyn-4.14.0-8edf7bcd.tar.gz';assert sha(archive)==record['source_archive_sha256']
verified=set()
with tarfile.open(archive) as tar:
    assert tar.pax_headers['comment']==record['roslyn_commit']
    for member in tar:
        name=member.name.partition('/')[2]
        if member.isfile() and name in wanted:
            assert hashlib.sha256(tar.extractfile(member).read()).hexdigest()==wanted[name],name
            assert sha(source/name)==wanted[name],name;verified.add(name)
assert verified==set(wanted)
feeds=[out/'feed',root/'runtime9-ns20-2/feed',root/'maintenance20-1/feed',root/'netstandard20-2/feed',Path('/clang64/lib/dotnet/library-packs')]
available={}
for feed in feeds:
    for file in feed.glob('*.nupkg'):available.setdefault(file.name.lower(),file)
cache_audits=[]
for assets_file in [out/'Microsoft.CodeAnalysis/obj/project.assets.json',out/'Microsoft.CodeAnalysis.CSharp/obj/project.assets.json',consumer/'obj/project.assets.json',consumer/'standard-consumer/obj/project.assets.json']:
    assets=json.loads(assets_file.read_text());folders=list(assets['packageFolders']);assert len(folders)==1;cache=posix(folders[0])
    for name,entry in assets['libraries'].items():
        if entry['type']!='package':continue
        ident,version=name.split('/');filename=ident.lower()+'.'+version+'.nupkg';assert filename in available,name
        package=available[filename];actual=cache/entry['path']/filename
        assert sha(actual)==sha(package),(name,assets_file)
        with zipfile.ZipFile(package) as z:
            for file in z.namelist():
                if file.endswith('.dll'):assert (cache/entry['path']/file).read_bytes()==z.read(file),(name,file)
        cache_audits.append(dict(assets=str(assets_file.relative_to(root)),package=name,sha256=sha(package)))
std=json.loads((consumer/'standard-consumer/obj/project.assets.json').read_text())
assert '.NETStandard,Version=v2.0' in std['targets']
report=dict(original_source_archive_inputs_verified=len(verified),source_archive_sha256=sha(archive),all_original_production_sources_unchanged=True,
            private_source_packages=packages,actual_compiler_and_consumer_package_references_verified=len(cache_audits),package_audits=cache_audits,
            all_cached_archives_and_dll_bytes_match_source=True,original_generated_compiler_sources=generated_inputs,
            original_codepages_minimum=record['projects']['Microsoft.CodeAnalysis']['original_package_minimums']['System.Text.Encoding.CodePages'],
            resolved_codepages_source_version=record['projects']['Microsoft.CodeAnalysis']['resolved_dependencies']['System.Text.Encoding.CodePages'],
            netstandard20_consumer_assets_verified=True,formal_pacman_installed=False,full_dependency_goal_complete=False)
(out/'source-package-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS original source/API/resource inputs, five compiler outputs, two netstandard2.0 packages and all actual compiler/consumer cache bytes')
