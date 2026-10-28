"""Match every tool DLL to original project output or installed source package bytes."""
from pathlib import Path
import hashlib
import json
import sys
import zipfile

root, host, gherkin = (Path(p).resolve() for p in sys.argv[1:])
source=root/'PowerShell-7.4.20'
sha=lambda data:hashlib.sha256(data).hexdigest()
names=('System.Management.Automation','Microsoft.PowerShell.CoreCLR.Eventing',
    'Microsoft.PowerShell.Commands.Utility','Microsoft.PowerShell.Commands.Management',
    'Microsoft.PowerShell.Security','Microsoft.Management.Infrastructure.CimCmdlets',
    'Microsoft.PowerShell.ConsoleHost','Microsoft.PowerShell.Commands.Diagnostics',
    'Microsoft.WSMan.Management','Microsoft.WSMan.Runtime')
project={name+'.dll':source/'src'/name/'bin/Release/net8.0'/(name+'.dll') for name in names}
packages={}
for path in Path('/clang64/lib/dotnet/library-packs').glob('*.nupkg'):
    with zipfile.ZipFile(path) as z:
        for item in z.namelist():
            if item.endswith('.dll'):
                packages.setdefault(sha(z.read(item)),[]).append(dict(package=path.name,asset=item))
metadata=json.loads((host/'source-runtime-metadata.json').read_text())
references=metadata['reference_metadata']
entry=json.loads((host/'source-console-entry.json').read_text())
assert entry['source_changes']==[]
assert entry['source_sha256']==sha((source/entry['original_source']).read_bytes())
assert entry['sdk_source_apphost_sha256']==sha(Path(entry['sdk_source_apphost_path']).read_bytes())
for name,digest in entry['outputs'].items(): assert sha((host/name).read_bytes())==digest,name
for name,digest in entry['references'].items(): assert sha((host/name).read_bytes())==digest,name
assert (host/'pwsh.exe').read_bytes()[:2]==b'MZ'
assert b'pwsh.dll' in (host/'pwsh.exe').read_bytes()
assert set(metadata['autoload_manifests'].values())==set(metadata['manifests'])
for relative, original in metadata['autoload_manifests'].items():
    assert (host/relative).read_bytes()==(source/original).read_bytes(),relative
result={}
for path in sorted(host.rglob('*.dll')):
    relative=path.relative_to(host).as_posix();digest=sha(path.read_bytes())
    if relative.startswith('ref/'):
        assert references[path.name]==digest,relative
        assert path.read_bytes()==(Path('/clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0')/path.name).read_bytes()
        result[relative]=dict(sha256=digest,source_reference_metadata=True)
    elif path.name=='SourcePowerShell.ModuleHost.dll':
        result[relative]=dict(sha256=digest,owned_host=True)
    elif relative=='pwsh.dll':
        assert digest==entry['outputs']['pwsh.dll']
        result[relative]=dict(sha256=digest,original_console_entry_source=entry['original_source'],source_sha256=entry['source_sha256'])
    elif path.name=='Gherkin.dll':
        assert path==host/'Modules/Pester/lib/Gherkin/core/Gherkin.dll'
        assert path.read_bytes()==gherkin.read_bytes()
        result[relative]=dict(sha256=digest,source_gherkin=True)
    elif path.name in project:
        assert path.read_bytes()==project[path.name].read_bytes(),relative
        result[relative]=dict(sha256=digest,original_project=project[path.name].relative_to(source).as_posix())
    else:
        assert digest in packages,('no source-built NuGet payload',relative,digest)
        result[relative]=dict(sha256=digest,installed_source_packages=packages[digest])
assert sum('original_project' in x for x in result.values())==10
assert sum('source_reference_metadata' in x for x in result.values())==len(references)
(root/'module-host-payload.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS every tool DLL matches one of ten original projects, the owned host, source Gherkin, source reference metadata or installed source NuGet payloads:',len(result),'assets')
