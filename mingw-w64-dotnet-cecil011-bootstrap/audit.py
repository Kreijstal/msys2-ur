"""Verify original compiler items, guards, signing inputs and actual package bytes."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

out=Path(sys.argv[1]).resolve();source=out/'source'
record=json.loads((out/'source-inputs.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
native_root=subprocess.check_output(['cygpath','-am',str(out)],text=True).strip()
def posix(value):
    value=value.replace('\\','/').rstrip('/')
    assert value.lower().startswith(native_root.lower()+'/'),value
    return out/value[len(native_root)+1:]
for rel,digest in record['original_file_sha256'].items():assert sha(source/rel)==digest,rel
assert record['source_changes']==0 and not record['NET40_profile_built']
policies={};cached=[]
for name,data in record['projects'].items():
    folder=(source/data['original_project']).parent;obj=folder/'obj/Release/netstandard2.0'
    actual={posix(line) for line in (obj/'recorded-Compile.txt').read_text().splitlines() if line}
    originals={source/rel for rel in data['original_cs']}
    assert originals.issubset(actual) and len(actual-originals)==1,(name,actual-originals)
    assert all(p.is_relative_to(obj) and p.name.endswith('.AssemblyAttributes.cs') for p in actual-originals)
    assert {p for p in actual if not p.is_relative_to(obj)}==originals
    # WriteLinesToFile treats semicolons inside the original properties as lists.
    values=(obj/'recorded-policy.txt').read_text().replace('\n',';').strip(';').split('|')
    assert len(values)==9 and values[0]=='netstandard2.0' and values[3]=='true' and values[4]==''
    assert values[5]=='false' and values[6]=='true' and values[7]=='' and values[8]=='7.3',values
    defines={n for n in values[1].split(';') if n};assert 'NET_CORE' in defines and 'DEBUG' not in defines
    assert ('INSIDE_ROCKS' in defines)==(name=='Mono.Cecil.Rocks')
    assert ('CECIL' in defines)==(name=='Mono.Cecil.Mdb')
    assert {n for n in values[2].split(';') if n}==({'0649'} if name=='Mono.Cecil.Pdb' else {'1701','1702'})
    policies[name]=values
    assets=json.loads((folder/'obj/project.assets.json').read_text());assert not assets.get('logs')
    assert len(assets['packageFolders'])==1
    cache=posix(next(iter(assets['packageFolders'])))
    for ident,item in assets['libraries'].items():
        if item['type']!='package':continue
        package,version=ident.split('/');filename=package.lower()+'.'+version+'.nupkg';installed=Path('/clang64/lib/dotnet/library-packs')/filename
        assert (cache/item['path']/filename).read_bytes()==installed.read_bytes()
        cached.append(dict(project=name,package=ident,archive_sha256=sha(installed)))
package=out/'feed/Mono.Cecil.0.11.0.nupkg'
with zipfile.ZipFile(package) as z:
    md=E.fromstring(z.read('Mono.Cecil.nuspec')).find('{*}metadata')
    assert md.findtext('{*}id')=='Mono.Cecil' and md.findtext('{*}version')=='0.11.0'
    assert {g.get('targetFramework') for g in md.find('{*}dependencies')}=={'.NETStandard2.0'}
    dlls={n for n in z.namelist() if n.endswith('.dll')}
    assert dlls=={'lib/netstandard2.0/'+n+'.dll' for n in record['projects']}
    for name,data in record['projects'].items():
        folder=(source/data['original_project']).parent
        for suffix in ['dll','pdb']:assert z.read('lib/netstandard2.0/'+name+'.'+suffix)==(folder/'bin/Release/netstandard2.0'/(name+'.'+suffix)).read_bytes()
    assert z.read('LICENSE.txt')==(source/'LICENSE.txt').read_bytes()
    assert z.read('licenses/Microsoft.Cci.Pdb/LICENSE')==(source/'symbols/pdb/Microsoft.Cci.Pdb/LICENSE').read_bytes()
    for p in (source/'symbols/mdb/Mono.CompilerServices.SymbolWriter').glob('*.cs'):
        assert z.read('licenses/Mono.CompilerServices.SymbolWriter/'+p.name+'.txt')==p.read_bytes()
    members={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
report=dict(original_source_files_verified=len(record['original_file_sha256']),selected_original_CSharp_inputs=sum(len(p['original_cs']) for p in record['projects'].values()),original_production_source_changes=0,original_NS2_guards_and_signing_key_retained=True,strict_WAE_probe=True,actual_compiler_policies=policies,exact_cached_source_archives=cached,package_sha256=sha(package),archive_members=members,NET40_profile_built=False,full_dependency_goal_complete=False)
(out/'producer-audit.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS original Cecil source/actual compiler items/guards/signing inputs, exact source restores and all four produced NS2 DLL/PDB pairs')
