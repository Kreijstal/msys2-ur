"""Verify the installed source SDK registration repair and all preserved payload bytes."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

archive,output=map(lambda p:Path(p).resolve(),sys.argv[1:])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record=json.loads(Path('/clang64/share/doc/dotnet-sdk8-servicing/netstandard21-registration.json').read_text())
assert record['source_sdk_package_sha256']=='a9a92676702275054ae88d09540071c5e2757055c17f0ac1040e0f22151fb0d0'
for name,digest in record['unchanged_seed_payload_files'].items():assert sha(Path('/')/name)==digest,name
assert sha(Path('/')/record['metadata_path'])==record['metadata_updated_sha256']
entry=E.parse(Path('/')/record['metadata_path']).find('.//KnownFrameworkReference[@Include="NETStandard.Library"]')
assert entry is not None and entry.attrib==record['restored_known_framework_reference']
files={};process=subprocess.Popen(['zstd','-dc',str(archive)],stdout=subprocess.PIPE)
with tarfile.open(fileobj=process.stdout,mode='r|') as t:
    for m in t:
        if m.isdir() or m.name.startswith('.'):continue
        assert m.isfile() and m.name.startswith('clang64/'),m.name
        data=t.extractfile(m).read();assert (Path('/')/m.name).read_bytes()==data,m.name
        files[m.name]=hashlib.sha256(data).hexdigest()
assert process.wait()==0
assert len(files)==len(record['unchanged_seed_payload_files'])+4
result=dict(package_archive_sha256=sha(archive),installed_payload_files_verified=len(files),
    unchanged_source_sdk_payload_files_verified=len(record['unchanged_seed_payload_files']),
    original_standard21_registration_verified=True,installed_files_sha256=files,
    sdk_managed_assemblies_recompiled=False,full_dependency_goal_complete=False)
output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n')
print('PASS installed source SDK payload, original framework registration and preserved bytes:',len(files),'files')
