"""Require actual SDK analyzer discovery and source-generated application bytes."""
from pathlib import Path
import hashlib,json,sys

out=Path(sys.argv[1]);record=json.loads((out/'verified-inventory.json').read_text())
lines=(out/'sample/analyzer-inputs.txt').read_text(encoding='utf-8-sig').replace('\\','/').splitlines()
selected=[p for p in lines if p.endswith('/System.Text.Json.SourceGeneration.dll')]
assert len(selected)==1 and '/analyzers/dotnet/roslyn4.4/cs/' in selected[0],selected
actual=out/'cache/system.text.json/8.0.5/analyzers/dotnet/roslyn4.4/cs/System.Text.Json.SourceGeneration.dll'
assert hashlib.sha256(actual.read_bytes()).hexdigest()==record['projects']['Gen4.4']['implementation_sha256']
assert len(list((out/'sample/obj/Release/net8.0/generated').rglob('*.cs')))>=5
assert (out/'sample/bin/Release/net8.0/System.Text.Json.dll').read_bytes()==(out/'bin/Release/net8.0/System.Text.Json.dll').read_bytes()
print('PASS exact SDK-selected source generator bytes, generated files and sample runtime payload')
