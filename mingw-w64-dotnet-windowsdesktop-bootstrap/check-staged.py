#!/usr/bin/env python3
"""Verify installed desktop payload paths and hashes against its source manifest."""
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as E

root=Path(sys.argv[1])
version='8.0.0-bootstrap.wpf.8.0.0'
framework=root/'shared/Microsoft.WindowsDesktop.App'/version
ref=root/'packs/Microsoft.WindowsDesktop.App.Ref'/version
runtime=root/'packs/Microsoft.WindowsDesktop.App.Runtime.win-x64'/version
manifest=json.loads((framework/'source-bootstrap.json').read_text())
assert manifest['frameworkVersion']==version
for entry in manifest['assemblies']:
    name=entry['name']+'.dll'
    assert hashlib.sha256((framework/name).read_bytes()).hexdigest()==entry['implementationSha256'],name
    assert hashlib.sha256((ref/'ref/net8.0'/name).read_bytes()).hexdigest()==entry['referenceSha256'],name
    assert (runtime/'runtimes/win-x64/lib/net8.0'/name).read_bytes()==(framework/name).read_bytes(),name
for pack,filename in ((ref,'FrameworkList.xml'),(runtime,'RuntimeList.xml')):
    for entry in E.parse(pack/'data'/filename).getroot():
        target=pack/entry.attrib['Path']
        assert target.is_file() and target.stat().st_size>0,str(target)
        if entry.get('Type')=='Native': assert target.read_bytes()==(framework/target.name).read_bytes(),str(target)
for entry in manifest['trustedNativeSeedDependencies']:
    assert hashlib.sha256((framework/entry['file']).read_bytes()).hexdigest()==entry['sha256'],entry['file']
desktop=root/'sdk/8.0.131/Sdks/Microsoft.NET.Sdk.WindowsDesktop'
assert (desktop/'tools/net8.0/PresentationBuildTasks.dll').is_file()
targets=desktop/'targets/Microsoft.WinFX.targets'
assert 'MarkupCompilePass1' in targets.read_text() and 'SourceBootstrapWpfUnavailable' not in targets.read_text()
legacy='8.0.0-bootstrap.7.0.20'
for family in ('shared/Microsoft.WindowsDesktop.App','packs/Microsoft.WindowsDesktop.App.Ref','packs/Microsoft.WindowsDesktop.App.Runtime.win-x64'):
    assert (root/family/legacy).is_dir(),family
print(f'PASS staged desktop payload: {len(manifest["assemblies"])} managed implementations/references, native hashes, SDK tasks and legacy versions')
