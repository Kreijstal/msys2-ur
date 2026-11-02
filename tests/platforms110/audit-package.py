"""Compare the final data package with pinned source and release graph semantics."""
from pathlib import Path
import hashlib
import io
import json
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

artifact, source, published, output = map(Path, sys.argv[1:])
sha = lambda b: hashlib.sha256(b).hexdigest()
assert sha(source.read_bytes()) == 'ccff0f90ffed453d9bd2a5843a9b25cc51103567bb1b0125c47213df74d2f09f'
assert sha(published.read_bytes()) == '15e338d24b5c39b4099389cc612841eb51ff13c07bb4829f97d39b27420e7023'
with tarfile.open(source) as t:
    assert t.pax_headers['comment'] == '8808e3e7f9749a168f86180496d6ea0f8e159db2'
    graph = t.extractfile('corefx-1.1.0/pkg/Microsoft.NETCore.Platforms/runtime.json').read()
    project = E.fromstring(t.extractfile('corefx-1.1.0/pkg/Microsoft.NETCore.Platforms/Microsoft.NETCore.Platforms.pkgproj').read())
    assert project.findtext('.//{*}PackageVersion') == '1.1.0'
    licenses = {n: t.extractfile('corefx-1.1.0/' + n).read() for n in ['LICENSE', 'THIRD-PARTY-NOTICES']}
assert sha(graph) == 'c011616db5f69bc2e5371641502313d78c0bd38491d2379a609c6970b7eb2595'
assert len(json.loads(graph)['runtimes']) == 117
with zipfile.ZipFile(published) as z:
    release_graph = z.read('runtime.json')
    assert json.loads(graph) == json.loads(release_graph)
    assert graph == release_graph.replace(b'\r\n', b'\n')
with tarfile.open(artifact) as t:
    files = {m.name.removeprefix('./'): t.extractfile(m).read() for m in t if m.isfile()}
prefix = 'clang64/'
package = files[prefix + 'lib/dotnet/library-packs/microsoft.netcore.platforms.1.1.0.nupkg']
with zipfile.ZipFile(io.BytesIO(package)) as z:
    assert z.read('runtime.json') == graph
    assert z.read('lib/netstandard1.0/_._') == b''
    assert not any(n.lower().endswith(('.dll', '.exe', '.pdb')) for n in z.namelist())
    md = E.fromstring(z.read('Microsoft.NETCore.Platforms.nuspec')).find('{*}metadata')
    assert md.findtext('{*}id') == 'Microsoft.NETCore.Platforms'
    assert md.findtext('{*}version') == '1.1.0'
    assert md.find('{*}repository').get('commit') == '8808e3e7f9749a168f86180496d6ea0f8e159db2'
    for name, data in licenses.items():
        assert z.read(name) == data
        assert files[prefix + 'share/licenses/dotnet-netcore-platforms110/' + name] == data
payload = {n: sha(b) for n, b in files.items() if n.startswith(prefix)}
assert len(payload) == 6, payload
for name in ['Check.cs', 'check.sh', 'README.md']:
    assert files[prefix + 'share/doc/dotnet-netcore-platforms110/' + name] == (Path('mingw-w64-dotnet-netcore-platforms110') / name).read_bytes()
report = dict(artifact=artifact.name, artifact_sha256=sha(artifact.read_bytes()),
              source_commit='8808e3e7f9749a168f86180496d6ea0f8e159db2',
              source_archive_sha256=sha(source.read_bytes()), nupkg_sha256=sha(package),
              original_graph_sha256=sha(graph), runtime_ids=117,
              exact_original_source_graph_and_licenses=True,
              release_graph_equal_after_newline_normalization=True,
              contains_implementation_binaries=False, payload_sha256=payload,
              full_dependency_goal_complete=False)
output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
