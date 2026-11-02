#!/usr/bin/env python3
"""Generate test expectations directly from the untouched upstream manifest."""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

manifest, winmeta, output = map(Path, sys.argv[1:])
ns = {"e": "http://schemas.microsoft.com/win/2004/08/events"}
provider = ET.parse(manifest).find(".//e:provider", ns)
metadata = ET.parse(winmeta).getroot()
types = {e.get("name"): int(e.get("value"), 0) for e in metadata.findall(".//e:inType", ns)}
templates = {e.get("tid"): list(e) for e in provider.findall("e:templates/e:template", ns)}
assert all(e.tag.endswith("}data") for t in templates.values() for e in t)
lines = ['struct ExpectedProperty { const wchar_t* name; unsigned short type; };',
         'struct ExpectedEvent { unsigned short id; unsigned char version; unsigned count; const ExpectedProperty* properties; };']
events = provider.findall("e:events/e:event", ns)
for index, event in enumerate(events):
    properties = templates.get(event.get("template"), [])
    values = [f'{{L{json.dumps(p.get("name"))}, {types[p.get("inType")]}}}' for p in properties]
    if not values:
        values = ['{nullptr, 0}']
    lines.append(f'static const ExpectedProperty properties{index}[] = {{{", ".join(values)}}};')
lines.append('static const ExpectedEvent expectedEvents[] = {')
for index, event in enumerate(events):
    count = len(templates.get(event.get("template"), []))
    lines.append(f'{{{int(event.get("value"), 0)}, {int(event.get("version", "0"), 0)}, {count}, properties{index}}},')
lines.append('};')
output.write_text('\n'.join(lines) + '\n')
