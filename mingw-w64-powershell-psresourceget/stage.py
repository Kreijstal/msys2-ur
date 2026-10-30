"""Stage the complete module and private dependency set from verified source outputs."""
import os
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,zipfile

source,prepared,cache,module=(Path(p) for p in sys.argv[1:]);module.mkdir();r=json.loads((prepared/'source-inventory.json').read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
for path,digest in r['original_module_assets'].items():
    data=(source/path).read_bytes();assert sha(data)==digest;target=module/path.removeprefix('src/');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
name='Microsoft.PowerShell.PSResourceGet';data=(prepared/'bin/Release/net8.0'/(name+'.dll')).read_bytes();assert sha(data)==r['implementation_sha256'];(module/(name+'.dll')).write_bytes(data)
private=module/'dependencies';private.mkdir();owned={};targets=json.loads((prepared/'obj/project.assets.json').read_text())['targets']['net8.0']
feed={p.name.lower():p for p in Path(os.environ['MINGW_PREFIX']+'/lib/dotnet/library-packs').glob('*.nupkg')}
licenses={}
for library,assets in targets.items():
    package,version=library.rsplit('/',1);lower=package.lower();package_file=cache/lower/version/(lower+'.'+version+'.nupkg')
    assert package_file.read_bytes()==feed[package_file.name.lower()].read_bytes(),library
    with zipfile.ZipFile(package_file) as z:
        legal=[p for p in z.namelist() if not p.endswith('/') and ('license' in Path(p).name.lower() or 'notice' in Path(p).name.lower())]
        native_legal=[];native_owner=None
        if not legal:
            native_owner=subprocess.check_output(['pacman','-Qqo',str(feed[package_file.name.lower()])],text=True).strip()
            for entry in subprocess.check_output(['pacman','-Qql',native_owner],text=True).splitlines():
                path=Path(entry)
                if '/share/licenses/' not in entry or not path.is_file():continue
                relative='licenses/'+lower+'/'+version+'/native/'+entry.split('/share/licenses/',1)[1]
                target=module/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(path.read_bytes())
                native_legal.append(dict(source=entry,target=relative,sha256=sha(path.read_bytes())))
            assert native_legal,('Missing original dependency license',library,native_owner)
        for path in legal+[p for p in z.namelist() if p.endswith('.nuspec')]:
            assert '..' not in Path(path).parts
            target=module/'licenses'/lower/version/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(path))
        licenses[library]=legal
        runtime_paths=list(assets.get('runtime',{}))
        for path,selection in assets.get('runtimeTargets',{}).items():
            assert selection['assetType']=='runtime' and selection['rid']=='win',(library,path,selection)
            runtime_paths.append(path)
        for path in runtime_paths:
            if not path.endswith('.dll'):continue
            data=z.read(path);filename=Path(path).name
            assert filename not in owned,(library,filename)
            output_path=Path(path) if path.startswith('runtimes/') else Path(filename)
            assert (prepared/'bin/Release/net8.0'/output_path).read_bytes()==data
            (private/filename).write_bytes(data);owned[filename]=dict(package=library,asset=path,sha256=sha(data),nuget_sha256=sha(package_file.read_bytes()),licenses=legal,native_license_owner=native_owner,native_license_assets=native_legal)
assert 'System.Management.Automation.dll' not in owned
(module/'source-inventory.json').write_bytes((prepared/'source-inventory.json').read_bytes())
(module/'source-dependencies.json').write_text(json.dumps(owned,indent=2)+'\n')
provenance=module/'source-build';provenance.mkdir()
for path in ['obj/Release/net8.0/ref/'+name+'.dll','bin/Release/net8.0/'+name+'.xml']:
    target=provenance/('ref/net8.0/' if path.endswith('.dll') else 'docs/')/Path(path).name
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((prepared/path).read_bytes())
for path in ['Library.csproj','upstream.proj','overlays/ContainerRegistryServerAPICalls.cs']:
    target=provenance/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((prepared/path).read_bytes())
here=Path(__file__).resolve().parent
for path in ['LICENSE','Notice.txt']:(module/path).write_bytes((source/path).read_bytes())
(module/'README.md').write_bytes((here/'README.md').read_bytes())
manifest={p.relative_to(module).as_posix():sha(p.read_bytes()) for p in module.rglob('*') if p.is_file()}
(module/'module-files.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
print('PASS complete original module assets and',len(owned),'private DLLs byte-identical to source-built NuGet runtime assets')
