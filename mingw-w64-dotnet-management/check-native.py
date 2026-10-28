"""Audit exports and imports of the newly compiled native WMI backend."""
from pathlib import Path
import json
import re
import subprocess
import sys

binary=Path(sys.argv[1])
result=subprocess.check_output(['/clang64/bin/llvm-readobj','--file-headers','--coff-imports','--coff-exports',str(binary)],text=True)
expected=json.loads((Path(__file__).resolve().parent/'native-exports.json').read_text())
exports=re.findall(r'Export \{.*?Name: ([^\r\n]+)',result,re.S)
imports=re.findall(r'Import \{.*?Name: ([^\r\n]+)',result,re.S)
assert len(expected)==65 and sorted(exports)==sorted(expected),(exports,expected)
assert 'IMAGE_FILE_MACHINE_AMD64' in result
for name in imports:
    name=name.lower()
    assert name in {'ole32.dll','oleaut32.dll','kernel32.dll','advapi32.dll'} or name.startswith('api-ms-win-crt-'),name
print('PASS WMI native backend: all 65 exact exports, AMD64, Windows/UCRT imports only')
