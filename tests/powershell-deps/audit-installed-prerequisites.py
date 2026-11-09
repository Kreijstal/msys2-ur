"""Read-only MSYS2 audit of each installed PowerShell build's recorded inputs.

Run with MSYS2 /usr/bin/python3; does not open database/WSMan connections.
"""
from pathlib import Path
import base64
import datetime
import hashlib
import json
import subprocess
import sys

installed = dict(line.split(' ', 1) for line in subprocess.run(
    ['/usr/bin/pacman', '-Q'], capture_output=True, text=True, check=True).stdout.splitlines())
results = {}
for prefix in map(Path, sys.argv[1:]):
    assert prefix.as_posix() in ['/clang64', '/ucrt64'], prefix
    closure_path = prefix / 'share/doc/powershell/license-closure.json'
    closure = json.loads(closure_path.read_text())
    wanted = closure['exact_build_package_versions']
    missing = [name for name in wanted if name not in installed]
    mismatched = {name: {'expected': version, 'actual': installed[name]}
                  for name, version in wanted.items()
                  if name in installed and installed[name] != version}
    feed = prefix / 'lib/dotnet/library-packs'
    files = {p.name.lower(): p for p in feed.iterdir() if p.is_file()}
    archives, missing_archives, hash_mismatches = {}, [], []
    paths, expected_owners = [], []
    for name, entry in closure['source_nuget_archives'].items():
        file = files.get(name.lower())
        if file is None:
            missing_archives.append(name)
            continue
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        paths.append(str(file))
        expected_owners.append(entry['native_owner'])
        archives[name] = {'sha256': digest, 'size': file.stat().st_size}
        if digest != entry['sha256']:
            hash_mismatches.append(name)
    owners = subprocess.run(['/usr/bin/pacman', '-Qoq', *paths],
                            capture_output=True, text=True, check=True).stdout.splitlines()
    ownership_matches = owners == expected_owners
    result = {'recorded_build_closure': str(closure_path),
              'closure_sha256': hashlib.sha256(closure_path.read_bytes()).hexdigest(),
              'package_requirements_checked': len(wanted),
              'missing_installed_packages': missing,
              'package_version_mismatches': mismatched,
              'source_archives_checked': len(archives),
              'missing_source_archives': missing_archives,
              'archive_hash_mismatches': hash_mismatches,
              'all_archive_owners_match_recorded_build': ownership_matches,
              'archives': archives}
    result['passed'] = not (missing or mismatched or missing_archives or hash_mismatches) and ownership_matches
    results[prefix.name] = result

query = r"""[pscustomobject]@{
    services=@(Get-CimInstance Win32_Service |
        Where-Object {$_.Name -match '^(MSSQL|SQLAgent|SQLBrowser|WinRM)'} |
        Select-Object Name,State,StartMode)
    localdb_installed_versions=@(
        if(Test-Path 'HKLM:\SOFTWARE\Microsoft\Microsoft SQL Server Local DB\Installed Versions'){
            Get-ChildItem 'HKLM:\SOFTWARE\Microsoft\Microsoft SQL Server Local DB\Installed Versions' |
                Select-Object -ExpandProperty PSChildName
        })
} | ConvertTo-Json -Depth 4"""
encoded = base64.b64encode(query.encode('utf-16le')).decode()
inventory = subprocess.run([
    '/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe',
    '-NoProfile', '-EncodedCommand', encoded], capture_output=True, text=True, check=True)
report = {'observed_at_UTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'environments': results, 'read_only_host_inventory': json.loads(inventory.stdout),
          'services_started': False, 'SQL_Server_EULA_accepted': False,
          'server_connection_attempted': False, 'full_dependency_goal_complete': False}
print(json.dumps(report, indent=2))
sys.exit(0 if results and all(r['passed'] for r in results.values()) else 1)
