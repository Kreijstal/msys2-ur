"""Prove runtime-loaded integration libraries belong to installed source packages."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import zipfile

out = Path(sys.argv[1])
prefix = Path(os.environ['MINGW_PREFIX'])
closure = json.loads((out / 'source-closure.json').read_text())
hashes = {}
for name in closure['source_package_owners']:
    with zipfile.ZipFile(prefix / 'lib/dotnet/library-packs' / name) as archive:
        for entry in archive.namelist():
            if entry.endswith('.dll'):
                digest = hashlib.sha256(archive.read(entry)).hexdigest()
                hashes.setdefault(digest, []).append({'package': name, 'asset': entry})
records = {}
baseline = '--baseline' in sys.argv[2:]
core_manifest_path = prefix / 'share/doc/dotnet-runtime8-servicing/source-payload.json'
core_manifest = json.loads(core_manifest_path.read_text())
expected_desktop_divergences = {'System.Configuration.ConfigurationManager', 'System.Drawing.Common',
                                'System.IO.Packaging', 'System.Security.Cryptography.ProtectedData', 'Microsoft.Win32.SystemEvents',
                                'System.Diagnostics.EventLog', 'System.DirectoryServices', 'System.Security.Permissions', 'System.Windows.Extensions'}
for mode in ['standalone', 'powershell-STA', 'powershell-MTA']:
    record = json.loads((out / (mode + '.json')).read_text())
    assert record['dependency_ids_loaded'] == 35 and len(record['cross_library_behavior_ids']) == 13
    assert record['assertions'] >= 60 and not record['provider_connection_attempted']
    if not baseline:
        assert len(record['assemblies']) == 36, 'Final check must inventory all direct assemblies and Windows.Extensions'
    if mode.startswith('powershell-'):
        assert record['apartment'] == mode.split('-')[1]
    owners, divergences = [], []
    for assembly in record['assemblies']:
        # The native assembly location is independently rehashed with MSYS paths.
        path = Path(subprocess.check_output(['cygpath', '-u', assembly['path']], text=True).strip())
        assert hashlib.sha256(path.read_bytes()).hexdigest() == assembly['sha256']
        if assembly['sha256'] in hashes:
            origin = {'matching_source_assets': hashes[assembly['sha256']]}
        elif assembly['name'] == 'System.Text.Encoding.CodePages':
            relative = 'shared/Microsoft.NETCore.App/8.0.31/System.Text.Encoding.CodePages.dll'
            assert path == prefix / 'lib/dotnet' / relative, path
            assert core_manifest['files'][relative] == assembly['sha256']
            origin = {'source_framework_manifest': str(core_manifest_path),
                      'manifest_sha256': hashlib.sha256(core_manifest_path.read_bytes()).hexdigest(),
                      'source_commit': core_manifest['source_commit'], 'relative_path': relative}
        else:
            assert baseline and prefix.name == 'clang64' and mode.startswith('powershell-'), assembly
            assert assembly['name'] in expected_desktop_divergences, assembly
            assert path.parent == prefix / 'lib/dotnet/shared/Microsoft.WindowsDesktop.App/8.0.0-bootstrap.wpf.8.0.0', path
            divergences.append(assembly)
            continue
        owners.append({'name': assembly['name'], 'sha256': assembly['sha256'], **origin})
    expected = (expected_desktop_divergences & set(record['cross_library_behavior_ids'])) if baseline and prefix.name == 'clang64' and mode.startswith('powershell-') else set()
    assert {a['name'] for a in divergences} == expected
    records[mode] = {'assertions': record['assertions'], 'source_owners': owners,
                     'unserviced_desktop_divergences': divergences}
package_prefix = 'mingw-w64-' + ('clang-x86_64' if prefix.name == 'clang64' else 'ucrt-x86_64')
packages = subprocess.check_output(['pacman', '-Q', package_prefix + '-powershell',
    package_prefix + '-dotnet-windows-compatibility', package_prefix + '-dotnet-sqlclient'], text=True).splitlines()
host = Path(os.environ.get('COMPAT_PWSH', str(prefix / 'bin/pwsh.exe')))
(out / ('runtime-baseline-identity.json' if baseline else 'runtime-source-identity.json')).write_text(json.dumps({'modes': records, 'baseline': baseline,
    'installed_packages': packages, 'host_executable': str(host),
    'host_executable_sha256': hashlib.sha256(host.read_bytes()).hexdigest(),
    'full_dependency_goal_complete': False}, indent=2) + '\n')
print('PASS source identities; ' + ('exact known desktop baseline differences recorded' if baseline else 'zero desktop selection divergences'))
