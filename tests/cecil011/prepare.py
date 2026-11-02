"""Prepare all four original Cecil0.11 NS2 projects, excluding executable fixtures."""
from pathlib import Path,PurePosixPath
import hashlib
import json
import sys
import tarfile
import xml.etree.ElementTree as E

archive,out=map(Path,sys.argv[1:]);assert not out.exists();out.mkdir();source=out/'source';source.mkdir()
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(archive.read_bytes())=='ef581a6ff59c8c5993f82ec5dadd470d185823e9407846c3ac992e23efdbcad3'
files={};removed={}
with tarfile.open(archive) as t:
    assert t.pax_headers['comment']=='12da1bf7e0e10278e05eeb23adfc72760bbb6668'
    for m in t:
        if not m.isfile():continue
        rel=m.name.partition('/')[2];p=PurePosixPath(rel);assert not p.is_absolute() and '..' not in p.parts
        data=t.extractfile(m).read()
        if p.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.mdb','.winmd','.obj','.lib','.resources','.zip'} or data[:2]==b'MZ':
            removed[rel]=sha(data);continue
        path=source/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);files[rel]=sha(data)
names={'Mono.Cecil':'Mono.Cecil.csproj','Mono.Cecil.Rocks':'rocks/Mono.Cecil.Rocks.csproj','Mono.Cecil.Mdb':'symbols/mdb/Mono.Cecil.Mdb.csproj','Mono.Cecil.Pdb':'symbols/pdb/Mono.Cecil.Pdb.csproj'}
projects={}
for name,rel in names.items():
    project=source/rel;tree=E.parse(project);assert tree.findtext('.//TargetFrameworks')=='netstandard2.0;net40'
    selected={}
    for item in tree.iter('Compile'):
        pattern=item.get('Include').replace('\\','/')
        # The original project items are explicit relative paths and simple globs.
        for p in sorted(project.parent.glob(pattern)):
            assert p.is_file();selected[p.resolve().relative_to(source.resolve()).as_posix()]=sha(p.read_bytes())
    assert selected
    projects[name]=dict(original_project=rel,original_frameworks=['netstandard2.0','net40'],selected_framework='netstandard2.0',original_cs=selected,original_NoWarn=tree.findtext('.//NoWarn'),source_changes=0)
(out/'source-inputs.json').write_text(json.dumps(dict(source_commit='12da1bf7e0e10278e05eeb23adfc72760bbb6668',source_archive_sha256=sha(archive.read_bytes()),original_file_sha256=files,excluded_binary_fixture_sha256=removed,projects=projects,source_changes=0,NET40_profile_built=False,compiler='source Roslyn4.4 original CLI/NET8 bootstrap',full_dependency_goal_complete=False),indent=2)+'\n')
(out/'Capture.targets').write_text('''<Project><Target Name="CaptureCecilInputs" BeforeTargets="CoreCompile">
<WriteLinesToFile File="$(IntermediateOutputPath)recorded-Compile.txt" Lines="@(Compile->'%(FullPath)')" Overwrite="true"/>
<WriteLinesToFile File="$(IntermediateOutputPath)recorded-ReferencePath.txt" Lines="@(ReferencePath->'%(FullPath)')" Overwrite="true"/>
<WriteLinesToFile File="$(IntermediateOutputPath)recorded-Analyzer.txt" Lines="@(Analyzer->'%(FullPath)')" Overwrite="true"/>
<WriteLinesToFile File="$(IntermediateOutputPath)recorded-policy.txt" Lines="$(TargetFramework)|$(DefineConstants)|$(NoWarn)|$(SignAssembly)|$(PublicSign)|$(GenerateAssemblyInfo)|$(TreatWarningsAsErrors)|$(Nullable)|$(LangVersion)" Overwrite="true"/>
</Target></Project>\n''')
# Keep the original NS2 files and dependency group; NET40 assets are not advertised.
spec=E.parse(source/'Mono.Cecil.nuspec');root=spec.getroot();metadata=root.find('{*}metadata')
metadata.find('{*}version').text='0.11.0'
for group in list(metadata.find('{*}dependencies')):
    if group.get('targetFramework')!='.NETStandard2.0':metadata.find('{*}dependencies').remove(group)
for file in list(root.find('files')):
    if file.get('target')!='lib/netstandard2.0':root.find('files').remove(file)
E.SubElement(root.find('files'),'file',src='LICENSE.txt',target='LICENSE.txt')
E.SubElement(root.find('files'),'file',src='symbols/pdb/Microsoft.Cci.Pdb/LICENSE',target='licenses/Microsoft.Cci.Pdb/LICENSE')
notices=source/'license-notices';notices.mkdir()
for p in (source/'symbols/mdb/Mono.CompilerServices.SymbolWriter').glob('*.cs'):
    # NuGet pack omits C# files from a nonsymbol package. Preserve every byte
    # under a text suffix so the original copyright/license headers ship.
    name=p.name+'.txt';(notices/name).write_bytes(p.read_bytes())
    E.SubElement(root.find('files'),'file',src='license-notices/'+name,target='licenses/Mono.CompilerServices.SymbolWriter/'+name)
E.indent(spec);spec.write(source/'NS2.nuspec',encoding='utf-8',xml_declaration=True)
print('PASS pinned original Cecil source inputs',{n:len(p['original_cs']) for n,p in projects.items()},'; excluded binary fixtures',len(removed))
