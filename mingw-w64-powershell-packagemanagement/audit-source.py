"""Compare actual Core compiler inputs with original projects and documented overlays."""
from pathlib import Path
import fnmatch
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as E

prepared,original,provider=(Path(p).resolve() for p in sys.argv[1:])
root=prepared/'oneget';record=json.loads((prepared/'source-inventory.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
overlays={item['path']:item['sha256'] for item in record['production_source_overlays']['files']}
resources={};result={}
namespaces={'Microsoft.PackageManagement':'Microsoft.PackageManagement.Internal',
    'Microsoft.PackageManagement.CoreProviders':'Microsoft.PackageManagement.Providers',
    'Microsoft.PackageManagement.MetaProvider.PowerShell':'Microsoft.PackageManagement.MetaProvider.PowerShell.Internal',
    'Microsoft.PowerShell.PackageManagement':'Microsoft.PowerShell.PackageManagement',
    'Microsoft.PackageManagement.NuGetProvider':'Microsoft.PackageManagement.NuGetProvider'}
for name,project in record['projects'].items():
    folder=root/'src'/name
    source=provider if name.endswith('.NuGetProvider') else original/'src'/name
    oldproject=source/('NuGetProvider.csproj' if name.endswith('.NuGetProvider') else name+'.csproj')
    original_files={p.relative_to(source).as_posix():p for p in sorted(source.rglob('*.cs'))}
    original_hashes={'src/'+name+'/'+p:sha(f) for p,f in original_files.items()}
    assert original_hashes==project['original_cs_files'],name
    removals=[]
    for group in E.parse(oldproject).getroot().findall('ItemGroup'):
        condition=group.get('Condition','')
        if condition and 'netstandard2.0' not in condition:continue
        for item in group.findall('Compile'):
            if item.get('Remove'):removals.extend(item.get('Remove').replace('\\','/').split(';'))
    # MSBuild's single * matches one path segment, not nested directories.
    def matches(path,pattern):
        parts=path.lower().split('/');glob=pattern.lower().split('/')
        assert '**' not in glob,'extend the independent evaluator for recursive patterns'
        return len(parts)==len(glob) and all(fnmatch.fnmatchcase(a,b) for a,b in zip(parts,glob))
    excluded={p for p in original_files if any(matches(p,pattern) for pattern in removals)}
    expected=set(original_files)-excluded
    actual=set();generated=[];sdk=[]
    for line in (folder/'source-compile-items.txt').read_text(encoding='utf-8-sig').splitlines():
        path=Path(subprocess.check_output(['cygpath','-u',line],text=True).strip()).resolve()
        relative=path.relative_to(folder).as_posix()
        if relative.startswith('obj/'):
            sdk.append(relative);continue
        if relative.startswith('gen/'):
            generated.append(relative);continue
        assert relative in original_files,('unlisted compiler input',name,relative)
        actual.add(relative)
        full=path.relative_to(root).as_posix()
        assert sha(path)==overlays.get(full,sha(original_files[relative])),full
    assert actual==expected,(name,expected-actual,actual-expected)
    constants=set((folder/'source-define-constants.txt').read_text(encoding='utf-8-sig').splitlines())
    assert {'CORECLR','DEBUG','NET8_0'}<=constants,name
    if name.endswith('.CoreProviders'):assert 'COREv1' in constants
    assert len(sdk)==2,(name,sdk)
    if name in namespaces:
        assert len(generated)==1,(name,generated)
        resx=source/'resources/Messages.resx'
        clazz=namespaces[name]+'.Resources.Messages'
        assert (folder/('resources/'+clazz+'.resx')).read_bytes()==resx.read_bytes()
        values={p.get('name').replace(' ','_'):p.findtext('value') for p in E.parse(resx).getroot().findall('data')}
        module='NuGetProvider' if name.endswith('.NuGetProvider') else name
        resources[name]={module+'.resources.'+clazz:values}
    else:assert not generated,name
    result[name]=dict(original_compiled_sources=len(actual),original_exclusions=sorted(excluded),
        original_sha256={p:sha(original_files[p]) for p in sorted(actual)},
        generated_sources={p:sha(folder/p) for p in generated},sdk_generated_sources=sdk,
        constants=sorted(constants),source_overlays={p:d for p,d in overlays.items() if p.startswith('src/'+name+'/')})
generator=root/'src/New-StronglyTypedCsFileForResx.ps1'
original_generator=original/'src'/generator.name
expected=original_generator.read_text(encoding='utf-8-sig').replace('$projectRoot = Split-Path $MyInvocation.InvocationName','$projectRoot = $PSScriptRoot').replace('$topLevel = git rev-parse --show-toplevel','$topLevel = Split-Path $projectRoot')
assert generator.read_text()==expected
assert sha(original_generator)==record['resource_generator']['original_sha256']
assert sha(generator)==record['resource_generator']['staged_sha256']
assert sum(len(values) for assembly in resources.values() for values in assembly.values())==295
(prepared/'compile-inventory.json').write_text(json.dumps(result,indent=2)+'\n')
(prepared/'expected-resources.json').write_text(json.dumps(resources,ensure_ascii=False,indent=2)+'\n')
print('PASS original Core compiler inputs/exclusions, three exact naming overlays, original generator algorithm, five generated classes and295 resource strings:',{k:v['original_compiled_sources'] for k,v in result.items()})
