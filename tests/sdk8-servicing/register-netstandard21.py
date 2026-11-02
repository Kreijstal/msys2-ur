"""Stage the declared source SDK4 package, restoring its original upstream Standard2.1 registration."""
from pathlib import Path
import copy
import hashlib
import json
import re
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

archive,out=(Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(),out
here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive)=='a9a92676702275054ae88d09540071c5e2757055c17f0ac1040e0f22151fb0d0'
provenance=json.loads((here/'inputs/installer8-framework-metadata-source.json').read_text())
assert sha(here/'inputs/installer8-GenerateBundledVersions.targets')==provenance['sha256']
assert sha(here/'inputs/installer8-Versions.props')==provenance['versions_sha256']
assert sha(here/'inputs/installer8-LICENSE.TXT')==provenance['license_sha256']
version=next(e.text for e in E.parse(here/'inputs/installer8-Versions.props').iter() if e.tag.split('}')[-1]=='NETStandardLibraryRefPackageVersion')
assert version=='2.1.0'
template=(here/'inputs/installer8-GenerateBundledVersions.targets').read_text()
original=E.fromstring(re.search(r'<KnownFrameworkReference Include="NETStandard.Library"\s+[^>]+/>',template).group())
assert original is not None
entry=copy.deepcopy(original)
entry.tag='KnownFrameworkReference'
assert entry.attrib==dict(Include='NETStandard.Library',TargetFramework='netstandard2.1',TargetingPackName='NETStandard.Library.Ref',TargetingPackVersion='$(NETStandardLibraryRefPackageVersion)')
entry.set('TargetingPackVersion',version)
out.mkdir(parents=True)
baseline={};info=None
process=subprocess.Popen(['zstd','-dc',str(archive)],stdout=subprocess.PIPE)
with tarfile.open(fileobj=process.stdout,mode='r|') as t:
    for m in t:
        if m.isdir():continue
        assert m.isfile() and '..' not in Path(m.name).parts and not m.name.startswith('/'),m.name
        data=t.extractfile(m).read()
        if m.name=='.PKGINFO':info=data.decode()
        if m.name.startswith('.'):continue
        assert m.name.startswith('clang64/'),m.name
        p=out/m.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);p.chmod(m.mode&0o777)
        baseline[m.name]=hashlib.sha256(data).hexdigest()
assert process.wait()==0
assert 'pkgver = 8.0.131-4\n' in info and 'pkgname = mingw-w64-clang-x86_64-dotnet-sdk8-servicing\n' in info
relative='clang64/lib/dotnet/sdk/8.0.131/Microsoft.NETCoreSdk.BundledVersions.props'
path=out/relative;before=E.fromstring(path.read_bytes())
assert before.find('.//KnownFrameworkReference[@Include="NETStandard.Library"]') is None
after=copy.deepcopy(before);group=E.SubElement(after,'ItemGroup');group.append(entry)
E.ElementTree(after).write(path,encoding='utf-8',xml_declaration=True)
actual=E.parse(path).getroot();newgroup=actual[-1]
assert len(newgroup)==1 and newgroup[0].attrib==entry.attrib
actual.remove(newgroup)
assert E.tostring(actual)==E.tostring(before),'All existing framework/host/runtime/linker metadata must remain unchanged'
unchanged={p:d for p,d in baseline.items() if p!=relative}
for p,d in unchanged.items():assert sha(out/p)==d,p
doc=out/'clang64/share/doc/dotnet-sdk8-servicing';doc.mkdir(parents=True,exist_ok=True)
result=dict(source_sdk_package=archive.name,source_sdk_package_sha256=sha(archive),source_package_version='8.0.131-4',
    upstream_installer=provenance,restored_known_framework_reference=entry.attrib,metadata_path=relative,
    metadata_original_sha256=baseline[relative],metadata_updated_sha256=sha(path),
    unchanged_seed_payload_files=unchanged,all_existing_framework_host_runtime_linker_metadata_retained=True,
    sdk_managed_assemblies_recompiled=False,full_dependency_goal_complete=False)
(doc/'netstandard21-registration.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS original upstream NETStandard2.1 SDK framework registration; retained',len(unchanged),'other source SDK payload files')
