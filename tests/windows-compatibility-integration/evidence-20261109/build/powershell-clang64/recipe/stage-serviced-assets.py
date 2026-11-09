"""Keep the required serviced assets explicit despite desktop pruning."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile

root, app = map(lambda p: Path(p).resolve(), sys.argv[1:])
here = Path(__file__).resolve().parent
prefix = Path(os.environ['MINGW_PREFIX'])
feed = prefix / 'lib/dotnet/library-packs'
sha = lambda data: hashlib.sha256(data).hexdigest()
required = {'Microsoft.Win32.SystemEvents': '8.0.0', 'System.Diagnostics.EventLog': '8.0.2',
            'System.DirectoryServices': '8.0.0', 'System.Security.Permissions': '8.0.0',
            'System.Windows.Extensions': '8.0.0', 'System.Configuration.ConfigurationManager': '8.0.1',
            'System.Drawing.Common': '8.0.31', 'System.IO.Packaging': '8.0.1',
            'System.Security.Cryptography.ProtectedData': '8.0.0'}
assets = {}
for name, version in required.items():
    archive = feed / (name.lower() + '.' + version + '.nupkg')
    with zipfile.ZipFile(archive) as package:
        selected = [p for p in ['runtimes/win/lib/net8.0/' + name + '.dll',
                                'lib/net8.0/' + name + '.dll'] if p in package.namelist()]
        assert selected, (name, archive)
        directory = selected[0].rsplit('/', 1)[0] + '/'
        companions = [entry for entry in package.namelist() if entry.startswith(directory)
                      and entry.endswith('.dll') and '/' not in entry[len(directory):]]
        for entry in companions:
            payload = package.read(entry)
            target = app / Path(entry).name
            target.unlink(missing_ok=True)
            target.write_bytes(payload)
            asset_name = target.stem
            assert asset_name not in assets, asset_name
            assets[asset_name] = {'archive': archive.name, 'archive_sha256': sha(archive.read_bytes()),
                                 'asset': entry, 'sha256': sha(payload), 'relative_path': target.name,
                                 'library': name + '/' + version, 'is_primary': asset_name == name}

inspector = root / 'serviced-asset-inspector'
inspector.mkdir(exist_ok=True)
shutil.copy2(here / 'ServicedAssetInfo.cs', inspector / 'Program.cs')
(inspector / 'Info.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
    '<TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost>'
    '<EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit>'
    '<TreatWarningsAsErrors>true</TreatWarningsAsErrors></PropertyGroup></Project>\n')
(inspector / 'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
native = lambda path: subprocess.check_output(['cygpath', '-am', str(path)], text=True).strip()
dotnet = str(prefix / 'lib/dotnet/dotnet.exe')
subprocess.run([dotnet, 'build', native(inspector / 'Info.csproj'), '-c', 'Release',
                '--configfile', native(inspector / 'NuGet.config'),
                '-p:UseSharedCompilation=false', '-v:minimal'], check=True)
metadata_path = inspector / 'versions.json'
subprocess.run([dotnet, native(inspector / 'bin/Release/net8.0/Info.dll'), native(metadata_path),
                *[native(app / (name + '.dll')) for name in assets]], check=True)
metadata = json.loads(metadata_path.read_text())
assert set(assets) == set(required) | {'System.Diagnostics.EventLog.Messages'}
assert {m['name'] for m in metadata} == set(assets)
assert {name for name, item in assets.items() if item['is_primary']} == set(required)
for item in metadata:
    assert item['assembly_version'] == '8.0.0.0', item
    if assets[item['name']]['is_primary']:
        assert item['file_version'] == '8.0.31.0' and 'v8.0.31' in item['product_version'], item
    assets[item['name']].update(item)

manifest_path = app / 'pwsh.deps.json'
original = manifest_path.read_bytes()
manifest = json.loads(original)
assert len(manifest['targets']) == 1
target = next(iter(manifest['targets'].values()))
for name in {a['library'] for a in assets.values()}:
    target[name]['runtime'] = {}
    target[name].pop('runtimeTargets', None)
for asset in assets.values():
    entry = {'assemblyVersion': asset['assembly_version']}
    if asset['file_version']:
        entry['fileVersion'] = asset['file_version']
    target[asset['library']]['runtime'][asset['relative_path']] = entry
manifest_path.unlink()
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
receipt = {'assets': assets, 'original_deps_sha256': sha(original),
           'staged_deps_sha256': sha(manifest_path.read_bytes()),
           'dependency_versions_and_contract_identities_preserved': True}
(root / (app.name + '-serviced-runtime-assets.json')).write_text(json.dumps(receipt, indent=2) + '\n')
stage_path = root / (app.name + '-stage.json')
stage = json.loads(stage_path.read_text())
stage['serviced_runtime_assets'] = {a['relative_path']: a for a in assets.values()}
stage['serviced_runtime_manifest'] = {'relative_path': manifest_path.name,
                                      'sha256': receipt['staged_deps_sha256']}
stage_path.write_text(json.dumps(stage, indent=2) + '\n')
print('PASS nine serviced source assets and actual file versions staged with explicit runtime entries')
