"""Audit final PolySharp package, original source bytes and explicit source ports."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import io
import json
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as E
import zipfile

artifact,source_archive,output=map(Path,sys.argv[1:])
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(source_archive.read_bytes())=='e89d37335624a6ca0f04870702d3d42fa3b3079ce9e0d99d79457b26d015d2d8'
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-polysharp115-bootstrap/'
record=json.loads(files[doc+'source-inputs.json']);ports=json.loads(files[doc+'source-ports.json'])
audit=json.loads(files[doc+'producer-audit.json']);checks=json.loads(files[doc+'producer-check-results.json'])
assert record['source_commit']=='02753db24d9685e54db06739eb63183d86eb5b62'
assert record['production_source_changes']==5 and not ports['warning_suppressions_added']
with tarfile.open(source_archive) as t:
    assert t.pax_headers['comment']==record['source_commit']
    originals={m.name.partition('/')[2]:t.extractfile(m).read() for m in t if m.isfile()}
assert {n:sha(v) for n,v in originals.items()}==record['original_file_sha256']
spec=importlib.util.spec_from_file_location('polysharp_ports',Path('mingw-w64-dotnet-polysharp115-bootstrap/ports.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
with tempfile.TemporaryDirectory(prefix='polysharp-final-source-audit-') as directory:
    root=Path(directory)
    for name,data in originals.items():
        path=root/'source'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    (root/'source-inputs.json').write_text(json.dumps(record))
    module.apply(root)
    assert json.loads((root/'source-ports.json').read_text())==ports
assert audit['production_source_changes']==5 and audit['source_ports']==ports['files']
assert audit['original_CSharp_inputs']==74 and audit['original_embedded_CSharp_inputs']==56
assert audit['original_SkipLocalsInit_target_executed']
assert audit['actual_compiler_policy']==['netstandard2.0','13.0','enable','true','strict','1.15.0.0','1.15.0','7','true','embedded']
assert checks['runtime']['exit_code']==0 and checks['runtime']['exact_Roslyn431_host']
assert all(c['exit_code']==0 for c in checks['commands'])
assert all(c['exit_code']==0 for c in checks['consumers']['commands'])
assert all(c['exit_code']==c['expected_exit_code'] for c in checks['guards']['commands'])
assert checks['guards']['minimum_compiler_metadata_guard'] and checks['guards']['legacy_project_guards']
package=files['clang64/lib/dotnet/library-packs/polysharp.1.15.0.nupkg']
assert sha(package)==audit['source_nupkg_sha256']
with zipfile.ZipFile(io.BytesIO(package)) as z:
    assert {n:sha(z.read(n)) for n in z.namelist()}==audit['archive_members']
    metadata=E.fromstring(z.read('PolySharp.nuspec')).find('{*}metadata')
    assert metadata.findtext('{*}id')=='PolySharp' and metadata.findtext('{*}version')=='1.15.0'
    assert metadata.findtext('{*}developmentDependency')=='true'
    assert [n for n in z.namelist() if n.endswith('.dll')]==['analyzers/dotnet/cs/PolySharp.SourceGenerators.dll']
    assert not any(n.startswith(('lib/','ref/')) for n in z.namelist())
    for prefix in ['build/','buildTransitive/']:
        assert z.read(prefix+'PolySharp.targets')==originals['src/PolySharp.SourceGenerators/PolySharp.targets']
    for name in ['README.md','icon.png']:
        assert z.read(name)==originals['src/PolySharp.Package/'+name]
assert files['clang64/share/licenses/dotnet-polysharp115-bootstrap/LICENSE']==originals['LICENSE']
for name in ['check.py','check-runtime.py','check-consumers.py','check-guards.py','README.md','inputs/Check.cs']:
    assert files[doc+name]==(Path('mingw-w64-dotnet-polysharp115-bootstrap')/name).read_bytes()
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),nupkg_sha256=sha(package),
    source_commit=record['source_commit'],source_files_verified=len(originals),production_source_files_ported=5,
    independently_replayed_source_ports=True,original_NS2_strict_nullable_WAE_and_style_policy=True,
    original_compiled_CSharp_inputs=74,unchanged_embedded_CSharp_inputs=56,
    exact_Roslyn431_generator_host_and_package_consumers_verified=True,
    original_targets_and_rejection_guards_verified=True,original_SDK9_release_host_replayed=False,
    broader_upstream_target_matrix_verified=False,
    payload_sha256={n:sha(v) for n,v in files.items() if n.startswith('clang64/')},full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
