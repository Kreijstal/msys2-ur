"""Keep upstream test bodies; launch their two child processes with our source host."""
from pathlib import Path
import hashlib
import json
import sys

source, output = (Path(p).resolve() for p in sys.argv[1:])
output.mkdir()
original=(source/'test/ThreadJob.Tests.ps1').read_bytes()
text=original.decode('utf-8-sig').replace('\r\n','\n')
old='$result = & "$PSHOME/pwsh" -c $script'
new='$result = Invoke-OwnedThreadJobChild $script'
assert text.count(old)==2
test=output/'ThreadJob.Tests.ps1'
test.write_text(text.replace(old,new),encoding='utf-8-sig')
(output/'source-test-overlay.json').write_text(json.dumps(dict(
    source_sha256=hashlib.sha256(original).hexdigest(),
    staged_sha256=hashlib.sha256(test.read_bytes()).hexdigest(),
    replacement_count=2,old=old,new=new,
    reason='Run unchanged runspace-lifetime script bodies in fresh source-host processes with explicit exact module import; shipping pwsh is not packaged yet.',
    constrained_language_suite='Not run: upstream suite mutates machine __PSLockdownPolicy. Production policy code is retained unchanged.'),indent=2)+'\n')
print('Staged all30 original ThreadJob cases; adapted only two child-process launchers')
