"""Prepare unchanged Humanizer2.14.1 sources for its original netstandard2.0 target."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

root,out=(Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(),out
out.mkdir(parents=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
archive=root/'humanizer-3ebc38de.tar.gz'
assert sha(archive)=='a98e80e9ca23c4ec17699481bd4b145e5477ba6f2ea8082956724428048c38db'
commit='3ebc38de585fc641a04b0e78ed69468453b0f8a1'
with tarfile.open(archive) as tar:
    assert tar.pax_headers['comment']==commit;tar.extractall(out,filter='data')
source=out/('Humanizer-'+commit);removed=[]
for p in source.rglob('*'):
    if p.is_file() and p.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.obj','.lib','.resources','.winmd'}:
        removed.append(dict(path=p.relative_to(source).as_posix(),sha256=sha(p)));p.unlink()
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
project=source/'src/Humanizer/Humanizer.csproj'
assert 'netstandard2.0' in E.parse(project).findtext('.//TargetFrameworks').split(';')
tree=E.Element('configuration');feeds=E.SubElement(tree,'packageSources');E.SubElement(feeds,'clear')
for name,path in [('source-standard',root/'netstandard20-2/feed'),('installed-source',Path('/clang64/lib/dotnet/library-packs'))]:E.SubElement(feeds,'add',key=name,value=native(path))
E.ElementTree(tree).write(out/'NuGet.config',encoding='utf-8',xml_declaration=True)
# Import this after the original SDK targets to add only package assets and
# compiler-input evidence. The original project and production sources stay intact.
tree=E.Element('Project');items=E.SubElement(tree,'ItemGroup');assets=out/'assets';assets.mkdir()
for file,target in [(source/'LICENSE','LICENSE'),(source/'src/Humanizer/Bytes/LICENSE','LICENSE.Bytes'),(source/'src/Humanizer/Inflections/LICENSE','LICENSE.Inflections')]:
    assert file.is_file();shutil.copyfile(file,assets/target)
    E.SubElement(items,'None',Include=native(assets/target),Pack='true',PackagePath='')
capture=E.SubElement(tree,'Target',Name='CaptureOriginalHumanizerInputs',BeforeTargets='CoreCompile')
for kind in ['Compile','ReferencePath','EmbeddedResource']:
    E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)'+kind+'.txt',Lines='@('+kind+"->'%(FullPath)')",Overwrite='true')
E.indent(tree);E.ElementTree(tree).write(out/'PackageAssets.targets',encoding='utf-8',xml_declaration=True)
inputs={p.relative_to(source).as_posix():sha(p) for p in [project,source/'src/Directory.build.props',*sorted((source/'src/Humanizer').rglob('*.cs')),*sorted((source/'src/Humanizer').rglob('*.resx')),source/'src/Humanizer/Humanizer.snk',source/'LICENSE',source/'src/Humanizer/Bytes/LICENSE',source/'src/Humanizer/Inflections/LICENSE']}
(out/'source-inputs.json').write_text(json.dumps(dict(source_commit=commit,archive_sha256=sha(archive),project=project.relative_to(source).as_posix(),original_inputs=inputs,production_cs_changes=0,project_changes=0,removed_binary_inputs=removed,full_dependency_goal_complete=False),indent=2)+'\n')
(out/'feed').mkdir()
print('Prepared unchanged original Humanizer netstandard2.0 project',len(inputs),'source/project/resource/key/license inputs')
