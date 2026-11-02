"""Extract the pinned source and capture actual original NET8 compilation inputs."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile,xml.etree.ElementTree as E
archive,out=(Path(p).resolve() for p in sys.argv[1:3]);assert not out.exists();out.mkdir(parents=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive)=='e7aef92baac548f21ecabf7fabbd940554327ee681791585e6fbeaea04356880'
with tarfile.open(archive) as tar:tar.extractall(out/'source',filter='data')
source=next((out/'source').iterdir()).resolve();removed=[]
for p in source.rglob('*'):
 if p.is_file() and p.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.obj','.lib','.resources'}:removed.append(p.relative_to(source).as_posix());p.unlink()
record=dict(source_root=source.as_posix(),source_commit='19c3ca7dc997dba2b3a86f6c666e9f717f34c8fe',source_archive_sha256=sha(archive),removed_binary_inputs=removed,original_target='net8.0',original_source_build=True,original_production_source_changes=0,full_dependency_goal_complete=False)
(out/'source-inputs.json').write_text(json.dumps(record,indent=2)+'\n')
project=E.Element('Project');target=E.SubElement(project,'Target',Name='CaptureSourceCompilerInputs',BeforeTargets='CoreCompile')
for kind in ['Compile','ReferencePath','Analyzer','EmbeddedResource']:
 E.SubElement(target,'WriteLinesToFile',File='$(CaptureRoot)/'+kind+'.txt',Lines='@('+kind+"->'%(FullPath)')",Overwrite='true')
E.ElementTree(project).write(out/'Capture.targets',encoding='utf-8',xml_declaration=True)
native=lambda p:Path(p).as_posix()
feed=subprocess.check_output(['cygpath','-am','/clang64/lib/dotnet/library-packs'],text=True).strip()
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="source" value="'+feed+'"/></packageSources></configuration>\n')
print('Prepared original source SolutionPersistence1.0.52;binary inputs removed:',len(removed))
