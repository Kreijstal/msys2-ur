"""Audit both original source selections, old references, policies and NuGet assets."""
from pathlib import Path
import hashlib,json,subprocess,sys,xml.etree.ElementTree as E,zipfile

root,contracts=(Path(s).resolve() for s in sys.argv[1:]);record=json.loads((root/'results.json').read_text());here=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
posix=lambda s:Path(subprocess.check_output(['cygpath','-au',s],text=True).strip()).resolve()
for name,digest in record['original_file_sha256'].items():assert sha(root/'source'/name)==digest,name
profiles={};all_sources=set()
for tfm,item in record['profiles'].items():
    original=root/'source/src/System.Threading.Tasks.Dataflow/src'/item['original_project']
    tree=E.parse(original).getroot()
    expected={(original.parent/e.get('Include').replace('\\','/')).resolve() for e in tree.findall('.//{*}Compile')}
    expected.add(root/'source/src/Common/src/System/SR.cs');all_sources.update(expected)
    obj=root/tfm/'obj/Release'/tfm
    actual={posix(s) for s in (obj/'Compile.txt').read_text().splitlines() if s}
    assert {p for p in actual if p.is_relative_to(root/'source')}==expected
    assert actual-expected=={root/tfm/'SR.Generated.cs',root/tfm/'BootstrapVersion.cs'}
    refs={posix(s) for s in (obj/'ReferencePath.txt').read_text().splitlines() if s}
    assert refs=={contracts/k/(k.split('/')[0]+'.dll') for k in item['reference_sha256']}
    for k,digest in item['reference_sha256'].items():assert sha(contracts/k/(k.split('/')[0]+'.dll'))==digest
    assert len(refs)==(19 if tfm=='netstandard1.0' else 21)
    assert not (obj/'Analyzer.txt').read_text().strip()
    policy=(obj/'policy.txt').read_text().replace('\n',';').strip(';').split('|')
    assert policy[0]==tfm and policy[2:]==['1701;1702','6','true'],policy
    assert 'DEBUG' not in policy[1]
    for feature in ['CONCURRENT_COLLECTIONS','FEATURE_TRACING']:assert (feature in policy[1])==(tfm=='netstandard1.1')
    assert tree.findtext('.//{*}AssemblyVersion')=='4.6.0.0'
    for doc in (root/'source/src/System.Threading.Tasks.Dataflow/src/XmlDocs').iterdir():
        if doc.is_file():assert (root/tfm/'XmlDocs'/doc.name).read_bytes()==doc.read_bytes()
    assert not json.loads((root/tfm/'obj/project.assets.json').read_text()).get('logs')
    profiles[tfm]=dict(original_CSharp_inputs=len(expected),reference_assemblies=len(refs),policy=policy,DLL_sha256=sha(root/tfm/'bin/Release'/tfm/'System.Threading.Tasks.Dataflow.dll'))
package=root/'feed/System.Threading.Tasks.Dataflow.4.6.0.nupkg'
provenance=json.loads((here/'inputs/published-provenance.json').read_text())
with zipfile.ZipFile(package) as z:
    md=E.fromstring(z.read('System.Threading.Tasks.Dataflow.nuspec')).find('{*}metadata')
    assert md.findtext('{*}id')=='System.Threading.Tasks.Dataflow' and md.findtext('{*}version')=='4.6.0'
    assert md.find('{*}repository').get('commit')==record['source_commit']
    groups={g.get('targetFramework'):{d.get('id'):d.get('version') for d in g} for g in md.findall('{*}dependencies/{*}group')}
    assert groups==dict(provenance['original_dependency_groups'],**{'.NETStandard2.0':{'NETStandard.Library':'[2.0.3]'}}),groups
    assert {n for n in z.namelist() if n.endswith('.dll')}=={'lib/'+t+'/System.Threading.Tasks.Dataflow.dll' for t in ['netstandard1.0','netstandard1.1','netstandard2.0']}
    for target,source in [('netstandard1.0','netstandard1.0'),('netstandard1.1','netstandard1.1'),('netstandard2.0','netstandard1.1')]:
        for ext,source_ext in [('dll','dll'),('xml','XML')]:assert z.read('lib/'+target+'/System.Threading.Tasks.Dataflow.'+ext)==(root/source/'bin/Release'/source/('System.Threading.Tasks.Dataflow.'+source_ext)).read_bytes()
    for lic in ['LICENSE','THIRD-PARTY-NOTICES']:assert z.read(lic)==(root/'source'/lic).read_bytes()
    members={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
report=dict(original_source_files_verified=len(record['original_file_sha256']),profiles=profiles,unique_original_CSharp_inputs=len(all_sources),production_CSharp_changes=0,original_compile_selections_and_feature_guards_preserved=True,original_NS10_NS11_dependency_groups_preserved=True,NS2_compatibility_DLL_bytes_identical_to_original_NS11=True,source_reference_DLL_bytes_verified=True,warnings_as_errors=True,package_sha256=sha(package),archive_members=members,full_historical_runtime_NuGet_closure_built=False,full_dependency_goal_complete=False)
(root/'producer-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
