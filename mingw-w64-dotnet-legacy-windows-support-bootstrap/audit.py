"""Audit original source selections, old-contract compiler inputs and archive profiles."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

root=Path(sys.argv[1]).resolve();record=json.loads((root/'source-inputs.json').read_text());contract=json.loads((Path(__file__).parent/'inputs/package-contract.json').read_text());reference_build=json.loads((root/'reference-build-results.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
def posix(value):return Path(subprocess.check_output(['cygpath','-au',value.strip()],text=True).strip())
def enabled(condition):
    if not condition:return True
    values={'TargetGroup':'','TargetsWindows':'true','TargetsUnix':'false'}
    def atom(value):
        match=re.fullmatch(r"'\$\(([^)]+)\)'\s*(==|!=)\s*'([^']*)'",value.strip());assert match,value
        return (values[match[1]]==match[3])==(match[2]=='==')
    return any(all(atom(term) for term in re.split(r'\s+and\s+',clause,flags=re.I)) for clause in re.split(r'\s+or\s+',condition,flags=re.I))
results={}
for name,item in record['libraries'].items():
    folder=root/name;source=folder/'source';project=source/item['original_project'];obj=folder/'obj/Release/netstandard1.3'
    for path,digest in item['original_file_sha256'].items():assert sha(source/path)==digest,path
    expected={source/'src/Common/src/System/SR.cs'}
    for group in E.parse(project).getroot():
        if group.tag.rsplit('}',1)[-1]!='ItemGroup' or not enabled(group.get('Condition')):continue
        for entry in group:
            if entry.tag.rsplit('}',1)[-1]!='Compile' or not enabled(entry.get('Condition')):continue
            value=entry.get('Include').replace('\\','/');path=Path(str(source/'src/Common/src')+value[len('$(CommonPath)'):]) if value.startswith('$(CommonPath)') else project.parent/value
            expected.add(path.resolve())
    actual={posix(line) for line in (obj/'Compile.txt').read_text().splitlines() if line}
    assert actual==expected|{folder/'SR.Generated.cs',folder/'BootstrapVersion.cs'},actual^expected
    policy=(obj/'policy.txt').read_text().replace('\n',';').strip(';').split('|');assert len(policy)==8 and policy[0:4]==['netstandard1.3','','true','false'] and policy[-2:]==['6','true'],policy
    assert 'DEBUG' not in policy[4] and 'TRACE' in policy[4] and policy[5]=='1701;1702',policy
    references={posix(line) for line in (obj/'ReferencePath.txt').read_text().splitlines() if line};wanted=set(Path(record['source_legacy_reference_pack']).glob('*.dll'));assert references==wanted and len(references)==16
    assert not (obj/'Analyzer.txt').read_text().strip()
    assets=json.loads((folder/'obj/project.assets.json').read_text());assert not assets.get('logs') and not assets['libraries']
    package=root/'feed'/(name+'.'+item['version']+'.nupkg');dll=folder/'bin/Release/netstandard1.3'/(name+'.dll')
    ref=folder/'contract'/(name+'.dll');ref_project=source/'src'/name/'ref'/(name+'.csproj')
    ref_inputs=[(ref_project.parent/e.get('Include')).resolve() for e in E.parse(ref_project).findall('.//{*}Compile')]
    assert reference_build[name]['original_source_sha256']=={p.relative_to(source).as_posix():sha(p) for p in ref_inputs}
    assert reference_build[name]['exit_code']==0 and reference_build[name]['source_CSharp_changes']==0 and reference_build[name]['output_sha256']==sha(ref)
    with zipfile.ZipFile(package) as z:
        metadata=E.fromstring(z.read(name+'.nuspec')).find('{*}metadata');assert metadata.findtext('{*}id')==name and metadata.findtext('{*}version')==item['version']
        assert metadata.find('{*}repository').get('commit')==item['source_commit']
        groups={g.get('targetFramework').replace('.','').lower():g for g in metadata.findall('{*}dependencies/{*}group')}
        assert [dict(d.attrib) for d in groups['netstandard13']]==contract[name]['original_NS13_dependencies']
        assert [dict(d.attrib) for d in groups['netstandard20']]==[{'id':'NETStandard.Library','version':'[2.0.3]'}]
        payloads={'lib/netstandard1.3/'+name+'.dll','lib/netstandard2.0/'+name+'.dll'}
        if contract[name]['original_NET46_DLL_identical_to_Windows_NS13']:payloads.add('lib/net46/'+name+'.dll');assert not list(groups['netframework46'])
        reference_payloads={'ref/netstandard1.3/'+name+'.dll','ref/netstandard2.0/'+name+'.dll'}
        if contract[name]['original_NET46_DLL_identical_to_Windows_NS13']:payloads.add('ref/net46/'+name+'.dll')
        assert {n for n in z.namelist() if n.endswith('.dll')}==payloads|reference_payloads
        for path in payloads:assert z.read(path)==dll.read_bytes()
        for path in reference_payloads:assert z.read(path)==ref.read_bytes()
        for license in ['LICENSE','THIRD-PARTY-NOTICES']:assert z.read(license)==(source/license).read_bytes()
        port=json.loads(z.read('source-port.json'));assert port['compiled_original_framework']=='netstandard1.3' and port['NS2_asset_identical_to_original_NS13_build'] and not port['original_NS13_NuGet_runtime_closure_verified']
        members={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
    results[name]=dict(original_CSharp_inputs=len(expected),original_contract_CSharp_inputs=len(ref_inputs),original_reference_assembly_version=reference_build[name]['original_reference_assembly_version'],original_contract_DLL_sha256=sha(ref),production_CSharp_changes=0,policy=policy,source_reference_DLL_sha256={p.name:sha(p) for p in references},original_source_files_verified=len(item['original_file_sha256']),package_sha256=sha(package),archive_members=members)
report=dict(libraries=results,original_NS13_windows_source_profiles=True,production_CSharp_changes=0,original_NS13_NuGet_dependencies_preserved=True,NS2_compatibility_assets_byte_identical=True,additional_NS2_base_contract={'NETStandard.Library':'[2.0.3]'},original_NS13_NuGet_runtime_closure_verified=False,full_dependency_goal_complete=False)
(root/'producer-audit.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS original Windows NS1.3 source/compiler/reference bytes, original dependency groups and disclosed NS2 compatibility assets')
