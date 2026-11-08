"""Validate real provider traffic, cancellation and cleanup from a fresh run."""
from pathlib import Path
import hashlib
import json
import re
import sys
import zipfile

root, prefix = map(Path, sys.argv[1:])
run, = root.glob('run-*')
state = json.loads((run/'results.json').read_text(encoding='utf-8-sig'))
for key in ['registration_exit', 'native_exit', 'managed_exit', 'host_exit']:
    assert state[key] == 0, (key, state[key])
assert state['powershell_exits'] == [0, 0]
for key in ['namespace_removed', 'autorecover_unchanged', 'winrm_unchanged', 'complete']:
    assert state[key] is True, key
assert not state['cleanup_errors']
assert state['com_keys_removed'] == [state['provider_clsid']]
assert json.loads((root/'provider-id.json').read_text())['clsid'] == state['provider_clsid']
read = lambda name: (run/name).read_text(encoding='utf-8-sig')
assert 'result=0 prompts=1 messages=1 progress=1 streams=2 finals=1 errors=1 failures=0' in read('native.out')
managed = read('managed.out')
checks = int(re.search(r'PASS (\d+) real provider-origin', managed).group(1))
assert checks == 116
assert managed.count('PASS actual provider callbacks/streams:') == 4
assert managed.count('PASS actual provider fault/cancellation:') == 8
provider = read('provider.out')
assert provider.count('PROVIDER cancellation-stream-abort=0') == 2
assert provider.count('PROVIDER cancellation-query=7') == 2
ps_checks = {}
for mode in ['STA', 'MTA']:
    ps_checks[mode] = int(re.search(r'PASS (\d+) original Invoke-CimMethod', read('powershell-'+mode+'.out')).group(1))
    assert ps_checks[mode] == 24
archive = prefix/'lib/dotnet/library-packs/microsoft.management.infrastructure.3.0.0.nupkg'
with zipfile.ZipFile(archive) as package:
    expected = package.read('lib/net8.0/Microsoft.Management.Infrastructure.dll')
assert expected == (root/'consumer/bin/Release/net8.0/Microsoft.Management.Infrastructure.dll').read_bytes()
result = {
    'state': state,
    'managed_checks': checks,
    'powershell_checks_per_mode': ps_checks,
    'provider_stream_writes_aborted_by_client_cancellation': 2,
    'provider_Context_Canceled_result': 'MI_RESULT_NOT_SUPPORTED (7) for this native decoupled local provider',
    'MMI_source_archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
    'MMI_DLL_sha256': hashlib.sha256(expected).hexdigest(),
    'fixture_binary_sha256': {
        name: hashlib.sha256((root/name).read_bytes()).hexdigest()
        for name in ['provider.dll', 'provider-host.exe', 'native-client.exe', 'consumer/bin/Release/net8.0/Check.dll']
    },
    'authenticated_remote_CIM_WSMan_verified': False,
    'full_dependency_goal_complete': False,
}
(root/'verified-results.json').write_text(json.dumps(result, indent=2)+'\n')
print(f'PASS {checks} provider checks, STA/MTA original cmdlets, server stream aborts, source bytes and cleanup')
