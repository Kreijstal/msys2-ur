"""Compare all published API declarations and identity, with no allowlist."""
from pathlib import Path
import json
import sys

baseline=json.loads(Path(sys.argv[1]).read_text())
actual=Path(sys.argv[2])
count=0
for name,expected in baseline.items():
    result=json.loads((actual/(name+'.json')).read_text())
    assert result['identity']==expected['identity'],name
    assert result['api']==expected['api'],(name,set(expected['api'])-set(result['api']),set(result['api'])-set(expected['api']))
    count+=len(result['api'])
assert count==382
print('PASS exact382 public/protected API declarations and all three assembly identities')
