"""Verify Release producer inputs and preserved original profile metadata."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

archive_root,out=(Path(p).resolve() for p in sys.argv[1:])
here=Path(__file__).resolve().parent
manifest=json.loads((out/'source-inputs.json').read_text())
evaluated=json.loads((out/'evaluated.json').read_text())
base=subprocess.check_output(['cygpath','-am',str(out)],text=True).strip()
def local(p):
    p=p.replace('\\','/');assert p.lower().startswith(base.lower()+'/'),p
    return out/p[len(base)+1:]
sources=0;groups_count=0
for name,r in manifest['projects'].items():
    assert r['configuration']=='Release' and r['production_source_changes']==0
    source=out/('maintenance-packages-'+r['commit'])
    if name!='System.Runtime.CompilerServices.Unsafe':
        assert 'DEBUG' not in evaluated[name]['properties']['DefineConstants'].split(';')
        actual={local(p) for p in (out/name/'obj/Release/netstandard2.0/Compile.txt').read_text().splitlines() if p}
        assert {p for p in actual if p.is_relative_to(source)}=={source/p for p in r['original_sources']},name
        sources+=len(r['original_sources'])
    publisher=E.parse(here/'inputs'/(name+'.publisher.nuspec')).getroot()
    expected={g.get('targetFramework'):{d.get('id'):dict(d.attrib) for d in g} for g in publisher.iter() if g.tag.endswith('group') and not g.get('targetFramework').startswith('.NETFramework')}
    package=out/'feed'/(name+'.'+r['version']+'.nupkg')
    with zipfile.ZipFile(package) as z:
        spec=E.fromstring(z.read(next(p for p in z.namelist() if p.endswith('.nuspec'))))
        actual={g.get('targetFramework'):{d.get('id'):dict(d.attrib) for d in g} for g in spec.iter() if g.tag.endswith('group')}
        assert actual==expected,(name,actual,expected)
        for target in expected:
            if target=='.NETStandard2.0':continue
            tfm=target.replace('.NETCoreApp','netcoreapp').replace('.NETStandard','netstandard')
            assert z.read('lib/'+tfm+'/_._')==b'',(name,target)
        assert not any(p.startswith('lib/net462/') for p in z.namelist())
        groups_count+=len(actual)
    policy=source/'eng/placeholderpackaging.targets'
    tree=E.parse(policy)
    assert tree.find('.//Compile[@Remove="@(Compile)"]') is not None
    assert tree.find('.//TfmSpecificPackageFile[@PackagePath="lib/$(TargetFramework)"]') is not None
assert sources==133 and groups_count==15,(sources,groups_count)
(out/'production-audit.json').write_text(json.dumps(dict(actual_original_csharp_compile_inputs_verified=sources,release_evaluation_without_debug=True,preserved_original_profile_dependency_groups=groups_count,inbox_placeholder_groups=10,legacy_framework_assets_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS 133 actual original Release CSharp inputs, all 15 original profile groups and ten inbox placeholders')
