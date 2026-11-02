"""Audit exact original source selection and source-only NS2 dependencies."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

root=Path(sys.argv[1]).resolve();source=root/'source';record=json.loads((root/'source-inputs.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,digest in record['original_file_sha256'].items():assert sha(source/name)==digest,name
base=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
def posix(value):
    value=value.replace('\\','/').rstrip('/');assert value.lower().startswith(base.lower()+'/'),value
    return root/value[len(base)+1:]
def enabled(condition):
    if not condition:return True
    parts=re.split(r'\s+(or|and)\s+',condition,flags=re.I);values=[]
    for part in parts:
        if part.lower() in {'or','and'}:values.append(part.lower());continue
        match=re.fullmatch(r"'\$\(TargetGroup\)'\s*(==|!=)\s*'([^']+)'",part.strip());assert match,part
        values.append(('netstandard'==match[2])==(match[1]=='=='))
    # The two selected project item conditions only use OR clauses.
    assert 'and' not in values
    return any(values[::2])
libraries={};total=0
for name,library in record['libraries'].items():
    folder=root/name;obj=folder/'obj/Release/netstandard2.0';project=source/library['original_project']
    expected=set()
    tree=E.parse(project).getroot()
    for group in tree:
        if group.tag.rsplit('}',1)[-1]!='ItemGroup' or not enabled(group.get('Condition')):continue
        for item in group:
            if item.tag.rsplit('}',1)[-1]!='Compile' or not enabled(item.get('Condition')):continue
            value=item.get('Include').replace('\\','/')
            path=(Path(str(source/'src/Common/src')+value[len('$(CommonPath)'):]) if value.startswith('$(CommonPath)') else project.parent/value).resolve()
            assert path.is_file(),path;expected.add(path)
    expected.add(source/'src/Common/src/System/SR.cs')
    actual={posix(s) for s in (obj/'Compile.txt').read_text().splitlines() if s}
    assert {p for p in actual if p.is_relative_to(source)}==expected,(name,actual^expected)
    assert actual-expected=={folder/'SR.Generated.cs',folder/'BootstrapVersion.cs'},actual-expected
    policy=(obj/'policy.txt').read_text().replace('\n',';').strip(';').split('|')
    assert len(policy)==6 and policy[0:2]==['netstandard2.0','netstandard'] and policy[4:]==['7.3','true'],policy
    assert 'DEBUG' not in policy[2] and ('FEATURE_ITEMREFAPI' in policy[2])==(name=='System.Collections.Immutable')
    assert policy[3]==('1591' if name=='System.Reflection.Metadata' else '1701;1702'),policy
    assets=json.loads((folder/'obj/project.assets.json').read_text());assert not assets.get('logs')
    expected_packages={'NETStandard.Library/2.0.3','Microsoft.NETCore.Platforms/1.1.0'}
    if name=='System.Reflection.Metadata':expected_packages.add('System.Collections.Immutable/1.5.0')
    assert set(assets['libraries'])==expected_packages,set(assets['libraries'])
    cache=posix(next(iter(assets['packageFolders'])))
    for ident,item in assets['libraries'].items():
        archive=ident.lower().replace('/','.')+'.nupkg'
        upstream=(root/'feed'/('System.Collections.Immutable.1.5.0.nupkg') if ident=='System.Collections.Immutable/1.5.0' else Path('/clang64/lib/dotnet/library-packs')/archive)
        assert (cache/item['path']/archive).read_bytes()==upstream.read_bytes()
        with zipfile.ZipFile(upstream) as z:
            for member in z.namelist():
                if member.endswith('.dll'):assert (cache/item['path']/member).read_bytes()==z.read(member)
    package=root/'feed'/(name+'.'+library['version']+'.nupkg')
    with zipfile.ZipFile(package) as z:
        metadata=E.fromstring(z.read(name+'.nuspec')).find('{*}metadata')
        assert metadata.findtext('{*}id')==name and metadata.findtext('{*}version')==library['version']
        assert metadata.find('{*}repository').get('commit')==record['source_commit']
        deps={e.get('id'):e.get('version') for e in metadata.iter() if e.tag.rsplit('}',1)[-1]=='dependency'}
        assert deps==({'System.Collections.Immutable':'[1.5.0]'} if name=='System.Reflection.Metadata' else {}),deps
        assert {n for n in z.namelist() if n.endswith('.dll')}=={'lib/netstandard2.0/'+name+'.dll'}
        assert z.read('lib/netstandard2.0/'+name+'.dll')==(folder/'bin/Release/netstandard2.0'/(name+'.dll')).read_bytes()
        for lic in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:assert z.read(lic)==(source/lic).read_bytes()
        members={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
    libraries[name]=dict(original_CSharp_inputs=len(expected),policy=policy,package_sha256=sha(package),archive_members=members)
    total+=len(expected)
report=dict(original_source_files_verified=len(record['original_file_sha256']),original_CSharp_inputs=total,production_CSharp_changes=0,original_NS2_source_conditions=True,source_only_reference_archives_and_DLL_bytes=True,libraries=libraries,other_original_profiles_built=False,original_buildtools_host_replayed=False,full_dependency_goal_complete=False)
(root/'producer-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
