"""Audit the original NS2 source selection and explicitly pruned dependency port."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

out=Path(sys.argv[1]).resolve();source=out/'source';r=json.loads((out/'source-inputs.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,digest in r['original_file_sha256'].items():assert sha(source/name)==digest,name
base=subprocess.check_output(['cygpath','-am',str(out)],text=True).strip()
def posix(value):
    value=value.replace('\\','/').rstrip('/');assert value.lower().startswith(base.lower()+'/'),value
    return out/value[len(base)+1:]
obj=out/'obj/Release/netstandard2.0'
actual={posix(line) for line in (obj/'Compile.txt').read_text().splitlines() if line}
framework=source/'src/Framework'
expected={p for p in framework.rglob('*.cs') if not p.is_relative_to(framework/'XamlTypes') and p.name!='BinaryWriterExtensions.cs'}
expected|={source/'src/Shared/Constants.cs',source/'src/Shared/BinaryWriterExtensions.cs'}
assert {p for p in actual if p.is_relative_to(source)}==expected
extras=actual-expected
assert out/'BootstrapVersion.cs' in extras and len(extras)==2,extras
assert all(p==out/'BootstrapVersion.cs' or p.is_relative_to(obj) and p.name.endswith('.AssemblyAttributes.cs') for p in extras)
policy=(obj/'policy.txt').read_text().replace('\n',';').strip(';').split('|')
assert len(policy)==6 and policy[0]=='netstandard2.0' and policy[3]=='7.3' and policy[4]=='' and policy[5]=='true',policy
defines={v for v in policy[1].split(';') if v}
assert {'STANDALONEBUILD','RUNTIME_TYPE_NETCORE','USE_MSBUILD_DLL_EXTN','WORKAROUND_COREFX_19110','FEATURE_RUNTIMEINFORMATION','FEATURE_PROCESSSTARTINFO_ENVIRONMENT'}.issubset(defines)
assert not defines&{'DEBUG','FEATURE_APPDOMAIN','FEATURE_XAML_TYPES','FEATURE_WIN32_REGISTRY','THISASSEMBLY'}
assets=json.loads((out/'obj/project.assets.json').read_text());assert not assets.get('logs')
assert {n for n,v in assets['libraries'].items() if v['type']=='package'}=={'NETStandard.Library/2.0.3','Microsoft.NETCore.Platforms/1.1.0'}
cache=posix(next(iter(assets['packageFolders'])))
for ident,item in assets['libraries'].items():
    if item['type']!='package':continue
    name,version=ident.split('/');filename=name.lower()+'.'+version+'.nupkg';p=Path('/clang64/lib/dotnet/library-packs')/filename
    assert (cache/item['path']/filename).read_bytes()==p.read_bytes()
    with zipfile.ZipFile(p) as z:
        for member in z.namelist():
            if member.endswith('.dll'):assert (cache/item['path']/member).read_bytes()==z.read(member)
package=out/'feed/Microsoft.Build.Framework.16.0.461.nupkg'
with zipfile.ZipFile(package) as z:
    md=E.fromstring(z.read('Microsoft.Build.Framework.nuspec')).find('{*}metadata')
    assert md.findtext('{*}id')=='Microsoft.Build.Framework' and md.findtext('{*}version')=='16.0.461'
    assert not any(e.tag.rsplit('}',1)[-1]=='dependency' for e in md.iter())
    assert md.find('{*}repository').get('commit')==r['source_commit']
    assert z.read('lib/netstandard2.0/Microsoft.Build.Framework.dll')==(out/'bin/Release/netstandard2.0/Microsoft.Build.Framework.dll').read_bytes()
    assert {n for n in z.namelist() if n.endswith('.dll')}=={'lib/netstandard2.0/Microsoft.Build.Framework.dll'}
    for name in ['LICENSE','THIRDPARTYNOTICES.txt']:assert z.read(name)==(source/name).read_bytes()
    members={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
result=dict(original_source_files_verified=len(r['original_file_sha256']),original_CSharp_inputs=len(expected),production_source_changes=0,actual_compiler_policy=policy,original_NS2_feature_guards=True,exact_source_reference_archives_and_DLL_bytes=True,pruned_unused_NS2_package_references=r['pruned_unused_NS2_package_references'],pruned_dependencies_require_API_and_runtime_reference_table_equality=True,package_sha256=sha(package),archive_members=members,NET472_profile_built=False,full_dependency_goal_complete=False)
(out/'producer-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS original Framework16 sources/feature guards, source-only reference bytes and NS2 package; dependency pruning awaits linked ABI/runtime gates')
