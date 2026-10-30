"""Check exact restored module assets, original compiler/resource inputs and API baselines."""
import os
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as E
import zipfile

out,module,source,provider,metadata=(Path(p).resolve() for p in sys.argv[1:])
here=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
golden=json.loads((here/'published-provenance.json').read_text())
record=json.loads((module/'source-build/provenance.json').read_text())
compiler=json.loads((module/'source-build/compile-inventory.json').read_text())
assets=json.loads((out/'obj/project.assets.json').read_text())
assert set(assets['libraries'])=={'PackageManagement/1.4.8.1'}
assert record['source_commit']==golden['source_commit'] and record['provider_commit']==golden['source_nuget_provider_commit']
assert len(record['projects'])==6 and record['production_csharp_changes']==3
assert set(compiler)==set(record['projects'])
total=0;originals={}
for name,item in record['projects'].items():
    folder=provider if name.endswith('.NuGetProvider') else source/'src'/name
    hashes={'src/'+name+'/'+p.relative_to(folder).as_posix():sha(p) for p in sorted(folder.rglob('*.cs'))}
    assert hashes==item['original_cs_files'],name
    for path,digest in compiler[name]['original_sha256'].items():assert sha(folder/path)==digest,(name,path)
    assert compiler[name]['original_compiled_sources']==len(compiler[name]['original_sha256'])
    assert {'CORECLR','DEBUG','NET8_0'}<=set(compiler[name]['constants'])
    total+=compiler[name]['original_compiled_sources']
    originals[name]=folder
assert total==277
overlay=record['production_source_overlays'];patch=here/'0002-qualify-original-async-enumerable.patch'
assert overlay['patch_sha256']==sha(patch)
assert len(overlay['files'])==3
with tempfile.TemporaryDirectory() as temp:
    root=Path(temp)
    for entry in overlay['files']:
        relative=Path(entry['path']).relative_to('src')
        target=root/relative;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text((source/'src'/relative).read_text(encoding='utf-8-sig'))
    subprocess.run(['patch','--fuzz=0','-p1','-i',str(patch)],cwd=root,check=True,stdout=subprocess.PIPE)
    for entry in overlay['files']:assert sha(root/Path(entry['path']).relative_to('src'))==entry['sha256']
assert record['resource_generator']['original_sha256']==sha(source/'src/New-StronglyTypedCsFileForResx.ps1')
assert record['resource_generator']['patch_sha256']==sha(here/'0001-resource-generator-use-script-root-for-archives.patch')
expected={}
for name in ('PackageManagement.psd1','PackageManagement.psm1','PackageManagement.Resources.psd1','PackageProviderFunctions.psm1','PackageManagement.format.ps1xml'):
    expected[name]=(source/'src/Microsoft.PowerShell.PackageManagement'/name).read_bytes()
dsc=source/'src/Microsoft.PackageManagement.DscResources'
for name in ('PackageManagementDscUtilities.psm1','PackageManagementDscUtilities.strings.psd1'):
    expected['DSCResources/'+name]=(dsc/name).read_bytes()
for name in ('MSFT_PackageManagement','MSFT_PackageManagementSource'):
    for path in sorted((dsc/name).rglob('*')):
        if path.is_file():expected['DSCResources/'+path.relative_to(dsc).as_posix()]=path.read_bytes()
for name,data in expected.items():assert (module/name).read_bytes()==data,name
assert len(expected)==15
binary=module/'coreclr/netstandard2.0';count=0
for name,baseline in golden['metadata_only_baselines'].items():
    file=binary/name;assert file.is_file(),name
    expected[file.relative_to(module).as_posix()]=file.read_bytes()
    api=json.loads((metadata/(name+'.api.json')).read_text())
    identity=json.loads((metadata/(name+'.identity.json')).read_text())
    assert api==baseline['api'],name
    assert {k:identity[k] for k in ('name','version','public_key_token','attributes')}==baseline['identity'],name
    assert identity['debuggable_flags']==263,name
    count+=len(api['api'])
assert count==2205
assert set(record['module_files'])==set(expected) and len(expected)==21
for name,digest in record['module_files'].items():assert sha(module/name)==digest,name
assert {p.relative_to(module).as_posix() for p in module.rglob('*.dll')}=={p for p in expected if p.endswith('.dll')}
assert not list(module.rglob('*.p7s'))
assert (module/'LICENSE').read_bytes()==(source/'LICENSE').read_bytes()
assert (module/'NuGetProvider-LICENSE.txt').read_bytes()==(provider/'LICENSE.txt').read_bytes()
resources=json.loads((module/'source-build/expected-resources.json').read_text())
namespaces={'Microsoft.PackageManagement':'Microsoft.PackageManagement.Internal',
    'Microsoft.PackageManagement.CoreProviders':'Microsoft.PackageManagement.Providers',
    'Microsoft.PackageManagement.MetaProvider.PowerShell':'Microsoft.PackageManagement.MetaProvider.PowerShell.Internal',
    'Microsoft.PowerShell.PackageManagement':'Microsoft.PowerShell.PackageManagement',
    'Microsoft.PackageManagement.NuGetProvider':'Microsoft.PackageManagement.NuGetProvider'}
for name,namespace in namespaces.items():
    module_name='NuGetProvider' if name.endswith('.NuGetProvider') else name
    base=module_name+'.resources.'+namespace+'.Resources.Messages'
    strings={p.get('name').replace(' ','_'):p.findtext('value') for p in E.parse(originals[name]/'resources/Messages.resx').getroot().findall('data')}
    assert resources[name]=={base:strings},name
assert sum(len(values) for item in resources.values() for values in item.values())==295
installed=Path(os.environ['MINGW_PREFIX']+'/lib/dotnet/library-packs/packagemanagement.1.4.8.1.nupkg')
if installed.is_file():
    with zipfile.ZipFile(installed) as z:same=all(z.read(name)==data for name,data in expected.items())
    if same:
        loose=Path(os.environ['MINGW_PREFIX']+'/lib/powershell/Modules/PackageManagement/1.4.8.1')
        for name,data in expected.items():assert (loose/name).read_bytes()==data,name
        print('PASS restored installed NuGet21 module files equal installed loose module bytes')
print('PASS PackageManagement277 original compiler inputs/five generated classes,295 resources,2205 APIs, six identities, three exact type-name overlays and complete Core module/DSC/license assets')
