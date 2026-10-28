"""Compare all shipped generated/static configuration text with the exact published baseline."""
from pathlib import Path
import json,sys
root=Path(sys.argv[1]);expected=json.loads(Path(sys.argv[2]).read_text())
for name,wanted in expected.items():
 actual=(root/name).read_text(encoding='utf-8-sig').replace('\r\n','\n')
 assert actual==wanted,name
assert len(expected)==611,len(expected)
print('PASS all611 generated/static configuration and documentation assets match independent published text')
