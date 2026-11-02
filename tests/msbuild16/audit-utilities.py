"""Check exact original Utilities source selection, resources and dependency archives."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

root=Path(sys.argv[1]).resolve();source=root/'source';record=json.loads((root/'source-inputs.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,digest in record['original_file_sha256'].items():assert sha(source/name)==digest,name
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
posix=lambda p:Path(subprocess.check_output(['cygpath','-au',p],text=True).strip())
original=source/'src/Utilities/Microsoft.Build.Utilities.csproj';expected=set(original.parent.rglob('*.cs'))
for item in E.parse(original).findall('.//Compile'):
    assert not item.get('Condition');expected.add((original.parent/item.get('Include').replace('\\','/')).resolve())
for name in ['FileSystemSources.proj','DebuggingSources.proj']:
    path=source/'src/Shared'/name
    for item in E.parse(path).findall('.//Compile'):
        value=item.get('Include').replace('$(MSBuildThisFileDirectory)','').replace('\\','/');expected.update(path.parent.glob(value))
obj=root/'obj/Release/netstandard2.0';actual={posix(p) for p in (obj/'Compile.txt').read_text().splitlines() if p}
assert {p for p in actual if p.is_relative_to(source)}==expected,actual^expected
assert len(actual-expected)==2 and root/'BootstrapVersion.cs' in actual-expected
policy=(obj/'policy.txt').read_text().replace('\n',';').strip(';').split('|');assert len(policy)==5 and policy[0]=='netstandard2.0' and policy[-2:]==['7.3','true'],policy
assert {'STANDALONEBUILD','RUNTIME_TYPE_NETCORE','FEATURE_RUNTIMEINFORMATION','FEATURE_PROCESSSTARTINFO_ENVIRONMENT','USE_MSBUILD_DLL_EXTN','WORKAROUND_COREFX_19110'}.issubset(set(policy[1].split(';')))
assert not set(policy[1].split(';'))&{'DEBUG','THISASSEMBLY','FEATURE_APPDOMAIN','FEATURE_XAML_TYPES'}
assert not (obj/'Analyzer.txt').read_text().strip()
assets=json.loads((root/'obj/project.assets.json').read_text());assert not assets.get('logs');cache=posix(next(iter(assets['packageFolders'])))
assert set(assets['libraries'])=={'Microsoft.Build.Framework/16.0.461','System.Collections.Immutable/1.5.0','System.Text.Encoding.CodePages/4.0.1','Microsoft.Win32.Registry/4.3.0','NETStandard.Library/2.0.3','Microsoft.NETCore.Platforms/1.1.0'},assets['libraries'].keys()
reference_paths={posix(p) for p in (obj/'ReferencePath.txt').read_text().splitlines() if p};verified=set()
for ident,item in assets['libraries'].items():
    archive=cache/item['path']/(ident.lower().replace('/','.')+'.nupkg');assert archive.is_file()
    with zipfile.ZipFile(archive) as z:
        for member in z.namelist():
            file=cache/item['path']/member
            if member.endswith('.dll') and file in reference_paths:assert file.read_bytes()==z.read(member);verified.add(file)
assert verified==reference_paths
package=root/'feed/Microsoft.Build.Utilities.Core.16.0.461.nupkg'
with zipfile.ZipFile(package) as z:
    metadata=E.fromstring(z.read('Microsoft.Build.Utilities.Core.nuspec')).find('{*}metadata');assert metadata.findtext('{*}id')=='Microsoft.Build.Utilities.Core' and metadata.findtext('{*}version')=='16.0.461'
    assert metadata.find('{*}repository').get('commit')==record['source_commit']
    dependencies={d.get('id'):d.get('version') for d in metadata.findall('.//{*}dependency')}
    assert dependencies=={name:'['+version+']' for name,version in record['exact_original_dependency_versions'].items()},dependencies
    assert [p for p in z.namelist() if p.endswith('.dll')]==['lib/netstandard2.0/Microsoft.Build.Utilities.Core.dll']
    assert z.read('lib/netstandard2.0/Microsoft.Build.Utilities.Core.dll')==(root/'bin/Release/netstandard2.0/Microsoft.Build.Utilities.Core.dll').read_bytes()
    for license in ['LICENSE','THIRDPARTYNOTICES.txt']:assert z.read(license)==(source/license).read_bytes()
    members={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
resources={}
for path in [source/'src/Utilities/Resources/Strings.resx',source/'src/Shared/Resources/Strings.shared.resx']:resources[path.name]={e.get('name'):e.findtext('value') for e in E.parse(path).findall('data')}
report=dict(original_source_files_verified=len(record['original_file_sha256']),original_CSharp_inputs=len(expected),production_CSharp_changes=0,actual_compiler_policy=policy,original_NS2_feature_guards=True,exact_original_dependency_versions=record['exact_original_dependency_versions'],all_actual_reference_DLL_bytes_verified_against_source_archives=True,source_resources=resources,package_sha256=sha(package),archive_members=members,NET472_profile_built=False,full_dependency_goal_complete=False)
(root/'producer-audit.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS original Utilities16 source selection/feature policy, exact dependency archives and NS2 package')
