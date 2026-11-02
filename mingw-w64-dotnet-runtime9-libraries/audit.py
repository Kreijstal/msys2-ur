"""Audit original sources, API baselines, generator outputs and actual package caches."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

root,out,consumer=(Path(p).resolve() for p in sys.argv[1:4])
net8_consumer=Path(sys.argv[4]).resolve() if len(sys.argv)==5 else root/'net8-consumer'
manifest=json.loads((out/'source-inputs.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=out/'runtime-source'
native_root=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
def posix(value):
    value=value.replace('\\','/').rstrip('/')
    assert value.lower().startswith(native_root.lower()+'/'),value
    return root/value[len(native_root)+1:]
wanted={}
def project_folder(name):
    area='bootstrap' if name.startswith('bootstrap:') else 'baseline-net8' if name.startswith('baseline:') else 'forwarder-netstandard21' if name.startswith('forwarder:') else 'libraries'
    return out/area/name.split(':')[-1]
for name,record in manifest['projects'].items():
    assert record['production_cs_changes']==0 and record['configuration']=='Release',name
    wanted[record['original_project']]=record['original_project_sha256']
    wanted.update(record['original_cs']);wanted.update(record['resource_files_sha256'])
    if record['key_policy']:wanted[record['key_policy']]=sha(source/record['key_policy'])
    original=source/record['original_project']
    folder=project_folder(name)
    tfm=record['bootstrap_host_framework'] or record['original_supported_framework']
    actual={posix(p) for p in (folder/'obj/Release'/tfm/'Compile.txt').read_text().splitlines() if p}
    assert {p for p in actual if p.is_relative_to(source)}=={source/p for p in record['original_cs']},name
    assert 'DEBUG' not in json.loads((out/'evaluated.json').read_text())[name]['properties']['DefineConstants'].split(';'),name
    for file in [original.parent/'PACKAGE.md',source/'LICENSE.TXT',source/'THIRD-PARTY-NOTICES.TXT']:
        if file.is_file():wanted[file.relative_to(source).as_posix()]=sha(file)
    for name,minimum in record['original_package_minimums'].items():
        if name in record['resolved_dependencies']:
            assert tuple(map(int,record['resolved_dependencies'][name].split('.')))>=tuple(map(int,minimum.split('.'))),(name,minimum)
for path,digest in json.loads((consumer/'api-source-inputs.json').read_text()).items():wanted[path]=digest
for path,field in [('src/libraries/Directory.Build.targets','shared_sources_policy_sha256'),('eng/generators.targets','generator_policy_sha256'),('src/libraries/System.Composition/src/System.Composition.csproj','composition_original_project_sha256'),('src/libraries/System.Runtime.InteropServices/gen/LibraryImportGenerator/Microsoft.Interop.LibraryImportGenerator.props','generator_configuration_props_sha256')]:wanted[path]=manifest[field]
for path in ['src/libraries/Directory.Build.props','eng/versioning.targets']:wanted[path]=sha(source/path)
archive=root/'runtime-v9.0.0.tar.gz';assert sha(archive)=='32755d528ead386762fb9da054249f6151ac78ef6a92f437044838cd0ab00def'
verified=set()
with tarfile.open(archive) as tar:
    assert tar.pax_headers['comment']==manifest['runtime_commit']
    for member in tar:
        name=member.name.partition('/')[2]
        if member.isfile() and name in wanted:
            assert hashlib.sha256(tar.extractfile(member).read()).hexdigest()==wanted[name],name
            assert sha(source/name)==wanted[name],name;verified.add(name)
assert verified==set(wanted)
packages={}
for package in (out/'feed').glob('*.nupkg'):
    with zipfile.ZipFile(package) as z:
        spec=E.fromstring(z.read(next(p for p in z.namelist() if p.endswith('.nuspec'))))
        md=next(e for e in spec if e.tag.endswith('metadata'));values={e.tag.rsplit('}',1)[-1]:e.text for e in md}
        name=values['id'];assert values['version']=='9.0.0'
        repo=next(e for e in md if e.tag.endswith('repository'));assert repo.get('commit')==manifest['runtime_commit']
        groups=[e for e in md.iter() if e.tag.endswith('group')]
        expected_tfms={'.NETStandard2.0','net8.0'} if name.startswith('System.Composition') else {'.NETStandard2.0','.NETStandard2.1'} if name=='Microsoft.Bcl.AsyncInterfaces' else {'.NETStandard2.0'}
        assert len(groups)==len(expected_tfms) and {e.get('targetFramework') for e in groups}==expected_tfms,(name,groups)
        deps={e.get('id'):e.get('version').strip('[]') for e in md.iter() if e.tag.endswith('dependency')}
        maintenance=set(json.loads(Path('/clang64/share/doc/dotnet-maintenance-netstandard/source-inputs.json').read_text())['projects'])
        for dep in (e for e in md.iter() if e.tag.endswith('dependency') and e.get('id') in maintenance):
            assert dep.get('version')==manifest['projects'][name]['resolved_dependencies'][dep.get('id')],(name,dep.attrib)
        if name=='System.Composition':
            assert deps=={n:'9.0.0' for n in manifest['order'] if n.startswith('System.Composition.')}
            assert not any(p.endswith('.dll') for p in z.namelist())
        else:
            assert deps==manifest['projects'][name]['resolved_dependencies'],(name,deps)
            for path in z.namelist():
                if path.startswith('lib/netstandard2.0/') and path.endswith('.dll'):
                    assert (out/'libraries'/name/'bin/Release/netstandard2.0'/path.removeprefix('lib/netstandard2.0/')).read_bytes()==z.read(path),(name,path)
                    assert (consumer/'library/bin/Release/netstandard2.0'/path.removeprefix('lib/netstandard2.0/')).read_bytes()==z.read(path),(name,path)
        if name.startswith('System.Composition.'):
            for path in z.namelist():
                if path.startswith('lib/net8.0/') and path.endswith('.dll'):
                    assert (out/'baseline-net8'/name/'bin/Release/net8.0'/path.removeprefix('lib/net8.0/')).read_bytes()==z.read(path),(name,path)
        if name=='Microsoft.Bcl.AsyncInterfaces':
            group=next(g for g in groups if g.get('targetFramework')=='.NETStandard2.1');assert len(group)==0
            assets=[p for p in z.namelist() if p.startswith('lib/netstandard2.1/')]
            assert assets==['lib/netstandard2.1/'+name+'.dll'],assets
            data=z.read(assets[0])
            assert data==(out/'forwarder-netstandard21'/name/'bin/Release/netstandard2.1'/(name+'.dll')).read_bytes()
            assert data==(net8_consumer/'bin/Release/net8.0'/(name+'.dll')).read_bytes()
        for text in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:
            assert z.read(text)==(source/text).read_bytes(),(name,text)
        packages[name]=dict(version=values['version'],sha256=sha(package),dependencies=deps)
assert set(packages)==set(manifest['order'])|{'System.Composition'}
library_feeds=[out/'feed',Path('/clang64/lib/dotnet/library-packs')]
tool_feeds=[Path('/clang64/lib/dotnet/library-packs')]
checks=[]
assets_files=[(project_folder(n)/'obj/project.assets.json',library_feeds) for n in manifest['projects']]
assets_files.extend([(consumer/'library/obj/project.assets.json',library_feeds),(consumer/'runner/obj/project.assets.json',tool_feeds),(net8_consumer/'obj/project.assets.json',library_feeds),(net8_consumer/'metadata/obj/project.assets.json',tool_feeds)])
for assets_file,feeds in assets_files:
    available={}
    for feed in feeds:
        for p in feed.glob('*.nupkg'):available.setdefault(p.name.lower(),p)
    assets=json.loads(assets_file.read_text());folders=list(assets['packageFolders']);assert len(folders)==1
    cache=posix(folders[0])
    for name,entry in assets['libraries'].items():
        if entry['type']!='package':continue
        ident,version=name.split('/');filename=ident.lower()+'.'+version+'.nupkg';assert filename in available,name
        package=available[filename];actual=cache/entry['path']/filename
        assert sha(actual)==sha(package),(name,assets_file,'cached package archive differs')
        with zipfile.ZipFile(package) as z:
            for p in z.namelist():
                if p.endswith('.dll'):assert (cache/entry['path']/p).read_bytes()==z.read(p),(name,p,assets_file)
        checks.append(dict(assets=str(assets_file.relative_to(root)),package=name,sha256=sha(package)))
generated={}
compiler=Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')
for name in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp','System.Collections.Immutable','System.Reflection.Metadata']:
    assert (consumer/'runner/bin/Release/net8.0'/(name+'.dll')).read_bytes()==(compiler/(name+'.dll')).read_bytes(),name
for name in manifest['order']:
    folder=out/'libraries'/name
    props=(folder/'obj/Release/netstandard2.0/Build.GeneratedMSBuildEditorConfig.editorconfig').read_text(encoding='utf-8-sig')
    assert 'build_property.TargetFrameworkIdentifier = .NETStandard' in props,name
    assert 'build_property.TargetFrameworkVersion = v2.0' in props,name
    assert 'build_property.LibraryImportGenerator_UseMarshalType = true' in props,name
    for file in (folder/'generated').rglob('*.cs'):generated[str(file.relative_to(out))]=sha(file)
assert any('System.Reflection.Metadata' in p and p.endswith('LibraryImports.g.cs') for p in generated)
report=dict(original_source_archive_inputs_verified=len(verified),source_archive_sha256=sha(archive),all_original_selected_sources_unchanged=True,
            source_packages=packages,actual_compiler_and_consumer_package_references_verified=len(checks),package_audits=checks,
            all_cached_package_archives_and_dll_bytes_match_source=True,all_shipped_resource_and_license_bytes_match_source=True,
            original_generator_configuration_checked_for_all_libraries=True,generated_source_sha256=generated,
            original_api_baseline_inputs=json.loads((consumer/'api-source-inputs.json').read_text()),
            original_standard21_forwarder_and_empty_dependency_group_verified=True,
            forwarder_consumer_results=json.loads((net8_consumer/'results.json').read_text()),
            maintenance_package_dependencies_are_compatible_minimums=True,
            formal_pacman_installed=bool(json.loads((consumer/'results.json').read_text())['formal_pacman_installed']),full_dependency_goal_complete=False)
(out/'source-package-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS pinned original source/API inputs, twelve packages, actual compiler/consumer cache bytes and original generator configuration')
