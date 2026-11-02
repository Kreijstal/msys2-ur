"""Independently compare MSBuild build records with the pinned source archives."""
from pathlib import Path
import hashlib,json,sys,tarfile,zipfile

evidence,archive,arcade,packages,output=(Path(p).resolve() for p in sys.argv[1:])
sha=lambda data:hashlib.sha256(data).hexdigest()
build=json.loads((evidence/'build4/results.json').read_text())
version=json.loads((evidence/'version-build/results.json').read_text())
assert sha(archive.read_bytes())=='fff679ff42b8f821d75c31921ad938900bf66c530a143ddef27c5ce239736e45'
assert sha(arcade.read_bytes())=='85d88d61027f75faa8a11fe04c0d1e0572eb3330610f1bb971954f6fb787ec9c'
originals={}
with tarfile.open(archive) as t:
    members={m.name.partition('/')[2]:m for m in t.getmembers() if m.isfile()}
    for r in build['projects']:
        for key in ['original_source_sha256','original_resource_sha256']:
            for path,digest in r[key].items():
                assert sha(t.extractfile(members[path]).read())==digest,path
                originals[path]=digest
        for name,pin in r['source_package_inputs'].items():
            if 'archive_sha256' not in pin:continue
            package=packages/(name.lower()+'.'+pin['version']+'.nupkg')
            assert sha(package.read_bytes())==pin['archive_sha256']
            with zipfile.ZipFile(package) as z:
                for path,digest in r['source_package_cs_sha256'].items():
                    if path.startswith(name+'/'):assert sha(z.read(path[len(name)+1:]))==digest
    assert sha(t.extractfile(members['eng/Versions.props']).read())==version['msbuild_original_override_sha256']
with tarfile.open(arcade) as t:
    task=next(m for m in t.getmembers() if m.name.endswith('/src/Microsoft.DotNet.Arcade.Sdk/src/CalculateAssemblyAndFileVersions.cs'))
    assert sha(t.extractfile(task).read())==version['original_task_sha256']
localization=evidence/'localized/results.json'
localized_inputs=0
if localization.is_file():
    with tarfile.open(archive) as t:
        members={m.name.partition('/')[2]:m for m in t.getmembers() if m.isfile()}
        for path,digest in json.loads(localization.read_text())['original_resource_inputs_sha256'].items():
            assert sha(t.extractfile(members[path]).read())==digest,path
            localized_inputs+=1
record=dict(msbuild_source_archive_sha256=sha(archive.read_bytes()),arcade_source_archive_sha256=sha(arcade.read_bytes()),original_compile_items=sum(len(r['original_source_sha256']) for r in build['projects']),distinct_original_source_and_resource_files=len(originals),source_package_compile_items=sum(len(r['source_package_cs_sha256']) for r in build['projects']),original_localization_inputs_verified=localized_inputs,all_selected_original_sources_and_resources_archive_exact=True,all_source_package_inputs_archive_exact=True,original_version_task_and_msbuild_override_archive_exact=True)
output.write_text(json.dumps(record,indent=2)+'\n')
print('PASS original input archive audit:',record['original_compile_items'],'Compile items,',record['source_package_compile_items'],'source-package items,',localized_inputs,'localization inputs')
