"""Stage the complete upstream Archive suite with one owned-path fixture change."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

source, output, module = (Path(p).resolve() for p in sys.argv[1:])
output.mkdir()
shutil.copytree(source/'Tests',output/'Tests')
# Original tests create new PowerShell instances. Their PSModulePath points at
# the test suite's parent, so stage exact module bytes for those fresh sessions.
shutil.copytree(module,output/'Microsoft.PowerShell.Archive')
test=output/'Tests/Pester.Commands.Cmdlets.Archive.Tests.ps1'
original=test.read_bytes()
text=original.decode('utf-8-sig').replace('\r\n','\n')
old='$sourcePath = "$env:SystemDrive$($DS)SourceDir"'
new='$sourcePath = "TestDrive:$($DS)OwnedArchiveRootSource"'
assert text.count(old)==1
text=text.replace(old,new)
comma_old='@{Entry="NUL.."}\n'
comma_new='@{Entry="NUL.."},\n'
assert text.count(comma_old)==1
text=text.replace(comma_old,comma_new)
test.write_text(text,encoding='utf-8-sig')
(output/'source-test-overlay.json').write_text(json.dumps(dict(
    source_sha256=hashlib.sha256(original).hexdigest(),
    staged_sha256=hashlib.sha256(test.read_bytes()).hexdigest(),
    overlays=[dict(old=old,new=new,reason='Exercise a filesystem drive-root path on the owned Pester TestDrive; avoid creation/deletion of a fixed C:\\SourceDir.'),
              dict(old=comma_old,new=comma_new,reason='Restore the missing test-data comma so all31 reserved-device cases execute, rather than only the first7.')]),indent=2)+'\n')
print('Staged complete upstream suite, owned TestDrive root fixture and all31 intended reserved-device cases')
