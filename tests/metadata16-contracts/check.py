"""Audit the four selected legacy compiler references as PE metadata only."""
from pathlib import Path
import json
import subprocess
import sys

directory, out, prefix = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir()
here = Path(__file__).parent
inspector = out / 'inspector'
command = [str(prefix / 'bin/python.exe'), '-X', 'utf8', str(here / 'build-inspector.py'), str(inspector), str(prefix)]
result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(out / 'inspector.log').write_bytes(result.stdout); assert result.returncode == 0, result.stdout.decode(errors='replace')
names = ['System.IO.Compression', 'System.Reflection.Extensions', 'System.Text.Encoding.Extensions', 'System.Runtime.InteropServices']
metadata = out / 'metadata.json'
inspect = [str(prefix / 'lib/dotnet/dotnet.exe'), str(inspector / 'bin/Release/net8.0/Inspect.dll'), str(metadata)] + [str(directory / (n + '.dll')) for n in names]
result = subprocess.run(inspect, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(out / 'metadata.log').write_bytes(result.stdout); assert result.returncode == 0, result.stdout.decode(errors='replace')
values = json.loads(metadata.read_text()); counts = {}
for name in names:
    filename = 'published-interop-ns11.json' if name.endswith('InteropServices') else name + '-reference-metadata.json'
    expected = json.loads((here / 'inputs' / filename).read_text())[name + '.dll']; actual = values[name + '.dll']
    assert actual['identity'] == expected['identity'], (name, 'identity')
    assert actual['api'] == expected['api'], (name, 'API')
    assert set(actual['references']) == set(expected['references']), (name, 'dependency identities')
    attrs = lambda rows: sorted(json.dumps(a, sort_keys=True) for a in rows)
    if not name.endswith('InteropServices'):
        assert attrs(actual['attributes']) == attrs(expected['attributes']), (name, 'attributes')
    assert any(a['type'] == 'System.Runtime.CompilerServices.ReferenceAssemblyAttribute' for a in actual['attributes'])
    counts[name] = len(actual['api'])
    print('PASS', name, counts[name], 'original API entries, identity, reference-only marker and dependencies')
(out / 'results.json').write_text(json.dumps(dict(commands=[dict(command=command, exit_code=0),dict(command=inspect, exit_code=0)],
    original_API_entries=counts, reference_assemblies_only=True, original_implementations_executed=False,
    full_NETStandard_targeting_pack=False, historical_runtimes_verified=False), indent=2) + '\n')
