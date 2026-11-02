"""Prepare PolySharp's original projects with explicit recorded source ports."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import sys
import tarfile
from ports import apply

archive, out = map(Path, sys.argv[1:])
assert not out.exists()
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='e89d37335624a6ca0f04870702d3d42fa3b3079ce9e0d99d79457b26d015d2d8'
out.mkdir()
source=out/'source';source.mkdir()
originals={}
with tarfile.open(archive) as t:
    assert t.pax_headers['comment']=='02753db24d9685e54db06739eb63183d86eb5b62'
    for m in t:
        if not m.isfile():continue
        rel=m.name.partition('/')[2]
        assert not PurePosixPath(rel).is_absolute() and '..' not in PurePosixPath(rel).parts
        data=t.extractfile(m).read()
        assert not rel.lower().endswith(('.dll','.exe','.nupkg','.pdb')) and data[:2]!=b'MZ',rel
        path=source/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        originals[rel]=hashlib.sha256(data).hexdigest()
(out/'source-inputs.json').write_text(json.dumps(dict(source_commit='02753db24d9685e54db06739eb63183d86eb5b62',source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),original_file_sha256=originals,production_source_changes=0,original_generator_framework='netstandard2.0',build_host_sdk='8.0.131 source bootstrap',compiler='5.0.0 source bootstrap on NET8',original_release_SDK='9.0.100',full_dependency_goal_complete=False),indent=2)+'\n')
# Imported after the original src/Directory.Build.targets; the upstream
# GenerateSkipLocalsInit target and root version/policy targets run unchanged.
(out/'Capture.targets').write_text('''<Project>
<Import Project="$(MSBuildThisFileDirectory)source/src/Directory.Build.targets"/>
<Target Name="RecordPolySharpInputs" BeforeTargets="CoreCompile;GenerateNuspec">
<WriteLinesToFile File="$(IntermediateOutputPath)recorded-Compile.txt" Lines="@(Compile->'%(FullPath)')" Overwrite="true"/>
<WriteLinesToFile File="$(IntermediateOutputPath)recorded-EmbeddedResource.txt" Lines="@(EmbeddedResource->'%(FullPath)|%(LogicalName)')" Overwrite="true"/>
<WriteLinesToFile File="$(IntermediateOutputPath)recorded-ReferencePath.txt" Lines="@(ReferencePath->'%(FullPath)')" Overwrite="true"/>
<WriteLinesToFile File="$(IntermediateOutputPath)recorded-Analyzer.txt" Lines="@(Analyzer->'%(FullPath)')" Overwrite="true"/>
<WriteLinesToFile File="$(IntermediateOutputPath)recorded-policy.txt" Lines="$(TargetFramework)|$(LangVersion)|$(Nullable)|$(TreatWarningsAsErrors)|$(Features)|$(AssemblyVersion)|$(VersionPrefix)|$(AnalysisLevel)|$(EnforceCodeStyleInBuild)|$(DebugType)" Overwrite="true"/>
</Target></Project>\n''')
apply(out)
print('PASS pinned PolySharp generator/package inputs',len(originals))
