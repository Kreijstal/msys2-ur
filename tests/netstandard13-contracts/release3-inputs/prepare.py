"""Extract unchanged SBRP sources for the exact legacy contract build matrix."""
from pathlib import Path
import hashlib
import json
import re
import sys
import tarfile
import xml.etree.ElementTree as E
import runpy

archive,legacy,out=(Path(x).resolve() for x in sys.argv[1:]);assert not out.exists();out.mkdir()
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='2b3136fab488246d0289e622797094e7c2eb29b35f67a9a5cd1312ef3ddfca79'
commit='5aeee2738338530a92d7f6caa2c7d5f569fed3c4';here=Path(__file__).parent
matrix=json.loads((here/'inputs/published-build-matrix.json').read_text())
provenance=json.loads((here/'inputs/build-matrix-provenance.json').read_text())
baseline=json.loads((here/'inputs/published-metadata.json').read_text())
assert hashlib.sha256(legacy.read_bytes()).hexdigest()=='986a512c70d55ed7a1ed8cbb9d8323017c9cc83e77e95e833c7b91f42e4ef601'
legacy_files={}
with tarfile.open(legacy) as t:
    assert t.pax_headers['comment']=='9688ddbb62c04189cac4c4a06e31e93377dccd41'
    for m in t:
        name=m.name.partition('/')[2]
        if m.isfile() and (name.startswith(('src/System.Diagnostics.Tools/ref/','src/System.Diagnostics.Contracts/ref/','src/System.Diagnostics.Debug/ref/','src/System.Runtime.InteropServices/ref/')) or name in {'LICENSE.TXT','THIRD-PARTY-NOTICES.TXT'}):legacy_files['corefx/'+name]=t.extractfile(m).read()
with tarfile.open(archive) as t:
    assert t.pax_headers['comment']==commit
    entries={m.name.partition('/')[2]:m for m in t if m.isfile()};records={};files=dict(legacy_files);active=set();generated={}
    def get(name):
        data=t.extractfile(entries[name]).read();files[name]=data;return data
    def select(key):
        if key in records:return
        assert key not in active,key;active.add(key)
        item=provenance[key];name=item['name'];version=item['version'];source=item['source'];framework=item['original_framework']
        assert re.fullmatch(r'netstandard1\.[0-3]',framework),framework
        if name=='System.Diagnostics.Contracts':
            assert key=='System.Diagnostics.Contracts/4.0.0.0' and framework=='netstandard1.0'
            select('System.Runtime/4.0.0.0')
            project='corefx/src/System.Diagnostics.Contracts/ref/System.Diagnostics.Contracts.csproj'
            assert E.fromstring(files[project]).findtext('.//{*}AssemblyVersion')==version
            header=get('src/referencePackages/src/system.diagnostics.tools/4.3.0/ref/netstandard1.0/System.Diagnostics.Tools.cs').decode('utf-8-sig').split('namespace System.CodeDom.Compiler')[0]
            generated['System.Diagnostics.Contracts.AssemblyInfo.cs']=header.replace('System.Diagnostics.Tools','System.Diagnostics.Contracts')
            records[key]=dict(name=name,assembly_version=version,package_version='4.0.1',original_project=project,original_framework=framework,source=source,source_sha256=hashlib.sha256(files[source]).hexdigest(),dependencies=['System.Runtime/4.0.0.0'],generated_assembly_attributes='System.Diagnostics.Contracts.AssemblyInfo.cs',original_CoreFX_reference_source=True)
            active.remove(key);return
        prefix='src/referencePackages/src/'+name.lower()+'/4.3.0/'
        assert source==prefix+'ref/'+framework+'/'+name+'.cs'
        projects=[n for n in entries if n.startswith(prefix) and n.endswith('.csproj')];assert len(projects)==1,(key,projects)
        project=projects[0];tree=E.fromstring(get(project));assert framework in tree.findtext('.//TargetFrameworks').split(';')
        data=get(source);text=data.decode('utf-8-sig')
        assert re.search(r'AssemblyVersion(?:Attribute)?\("'+re.escape(version)+r'"\)',text),key
        assert prefix+'Customizations.props' not in entries,(key,'Review customization before building')
        declared=set()
        for group in tree.findall('ItemGroup'):
            condition=group.get('Condition')
            if condition:
                normalized=condition.replace(' ','');assert normalized.startswith("'$(TargetFramework)'=="),condition
                if normalized!="'$(TargetFramework)'=='"+framework+"'":continue
            declared.update(e.get('Include') for e in group.findall('PackageReference'))
        dependencies=[]
        for ref in matrix[key]['references']:
            ident,rest=ref.split(', Version=');assert ident in declared,(key,ident,declared)
            dep=ident+'/'+rest.split(',')[0];assert dep in matrix,dep;select(dep);dependencies.append(dep)
        extra={}
        if name=='System.Diagnostics.Debug':
            assert key=='System.Diagnostics.Debug/4.0.10.0' and framework=='netstandard1.3'
            generated['System.Diagnostics.Debug.AssemblyInfo.cs']=text.split('namespace System.Diagnostics')[0]
            source='corefx/src/System.Diagnostics.Debug/ref/System.Diagnostics.Debug.cs';data=files[source]
            project='corefx/src/System.Diagnostics.Debug/ref/System.Diagnostics.Debug.csproj'
            extra=dict(generated_assembly_attributes='System.Diagnostics.Debug.AssemblyInfo.cs',original_CoreFX_reference_source=True,SBRP_missing_Conditional_DEBUG_attributes_corrected_by_original_source=True)
        if name=='System.Diagnostics.Tools':
            assert key=='System.Diagnostics.Tools/4.0.0.0'
            generated['System.Diagnostics.Tools.AssemblyInfo.cs']=text.split('namespace System.CodeDom.Compiler')[0]
            source='corefx/src/System.Diagnostics.Tools/ref/System.Diagnostics.Tools.cs';data=files[source]
            project='corefx/src/System.Diagnostics.Tools/ref/System.Diagnostics.Tools.csproj'
            extra=dict(generated_assembly_attributes='System.Diagnostics.Tools.AssemblyInfo.cs',original_CoreFX_reference_source=True,SBRP_missing_SuppressMessageAttribute_corrected_by_original_source=True)
        if name=='System.Runtime.InteropServices':
            assert key=='System.Runtime.InteropServices/4.0.20.0'
            original='corefx/src/System.Runtime.InteropServices/ref/System.Runtime.InteropServices.cs'
            generated['Interop.Ported.cs']=runpy.run_path(str(here/'port-interop.py'))['port'](text,files[original].decode('utf-8-sig'))
            extra=dict(generated_port_source='Interop.Ported.cs',port_original_CoreFX_source=original,restored_original_attribute_classes=['ClassInterfaceAttribute','ComDefaultInterfaceAttribute','GuidAttribute','InterfaceTypeAttribute'],restored_original_struct_declarations=['BINDPTR','ELEMDESC','VARDESC'])
        records[key]=dict(name=name,assembly_version=version,package_version='4.3.0',original_project=project,original_framework=framework,source=source,source_sha256=hashlib.sha256(data).hexdigest(),dependencies=dependencies,declared_project_dependencies=sorted(declared),**extra)
        active.remove(key)
    roots={}
    for filename,item in baseline.items():
        name=filename.removesuffix('.dll');key=name+'/'+item['identity'].split('Version=')[1].split(',')[0]
        select(key);roots[name]=key
    assert set(records)==set(matrix)==set(provenance)
    for name in ['LICENSE.txt','src/SourceBuildAssemblyMetdata.cs','src/referencePackages/Directory.Build.props','src/referencePackages/Directory.Build.targets']:get(name)
source=out/'source'
for name,data in files.items():
    assert not name.lower().endswith(('.dll','.exe','.nupkg')) and data[:2]!=b'MZ',name
    p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
suppression=[]
for node in E.parse(source/'src/referencePackages/Directory.Build.props').iter('NoWarn'):
    suppression.extend(x for x in re.split('[;,]',node.text.replace('$(NoWarn)','')) if x)
for name,text in generated.items():(out/name).write_text(text)
record=dict(source_commit=commit,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),CoreFX_source_commit='9688ddbb62c04189cac4c4a06e31e93377dccd41',CoreFX_archive_sha256=hashlib.sha256(legacy.read_bytes()).hexdigest(),original_file_sha256={n:hashlib.sha256(v).hexdigest() for n,v in files.items()},reference_only=True,production_source_changes=1,original_source_files_modified_in_place=0,generated_source_sha256={n:hashlib.sha256(text.encode()).hexdigest() for n,text in generated.items()},original_NoWarn=suppression,SDK_default_NoWarn=['1701','1702'],libraries=records,root_contracts=roots,CodePages_Diagnostics_Contracts_reference_built=True,CodePages_Diagnostics_Contracts_runtime_package_built=False,full_NETStandard13_runtime_package_closure_built=False)
(out/'source-inputs.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS prepared',len(records),'original legacy build contracts for',len(roots),'root contracts')
