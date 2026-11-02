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
assert sha(source.read_bytes()) == '80c9002e283d6fea5f75c9c7210a09a9a53038aed6bb661fe74b144d6f8a93ac'
assert sha(published.read_bytes()) == '8184103bbceca86f8eb4de32c184327ec8a0812db39b1c38f9c3d794af850794'
with tarfile.open(source) as t:
    assert t.pax_headers['comment'] == '6851cc781ad2ff33d4a0f429a6fc1ab85abaff86'
    graph = t.extractfile('corefx-6851cc781ad2ff33d4a0f429a6fc1ab85abaff86/pkg/Microsoft.NETCore.Platforms/runtime.json').read()
    project = E.fromstring(t.extractfile('corefx-6851cc781ad2ff33d4a0f429a6fc1ab85abaff86/pkg/Microsoft.NETCore.Platforms/Microsoft.NETCore.Platforms.pkgproj').read())
    assert project.findtext('.//{*}PackageVersion') == '2.1.2'
    licenses = {n: t.extractfile('corefx-6851cc781ad2ff33d4a0f429a6fc1ab85abaff86/' + n+'.TXT').read() for n in ['LICENSE', 'THIRD-PARTY-NOTICES']}
assert sha(graph) == 'e5c6c05c5f65ba037d080e35cf04ee29e2796e55281cd71b4e7911a74e9b9824'
assert len(json.loads(graph)['runtimes']) == 515
with zipfile.ZipFile(published) as z:
    release_graph = z.read('runtime.json')
    assert json.loads(graph) == json.loads(release_graph)
    assert graph == release_graph.replace(b'\r\n', b'\n')
with tarfile.open(artifact) as t:
    files = {m.name.removeprefix('./'): t.extractfile(m).read() for m in t if m.isfile()}
prefix = 'clang64/'
package = files[prefix + 'lib/dotnet/library-packs/microsoft.netcore.platforms.2.1.2.nupkg']
with zipfile.ZipFile(io.BytesIO(package)) as z:
    assert z.read('runtime.json') == graph
    assert z.read('lib/netstandard1.0/_._') == b''
    assert not any(n.lower().endswith(('.dll', '.exe', '.pdb')) for n in z.namelist())
    md = E.fromstring(z.read('Microsoft.NETCore.Platforms.nuspec')).find('{*}metadata')
    assert md.findtext('{*}id') == 'Microsoft.NETCore.Platforms'
    assert md.findtext('{*}version') == '2.1.2'
    assert md.find('{*}repository').get('commit') == '6851cc781ad2ff33d4a0f429a6fc1ab85abaff86'
    for name, data in licenses.items():
        assert z.read(name) == data
        assert files[prefix + 'share/licenses/dotnet-netcore-platforms212/' + name] == data
payload = {n: sha(b) for n, b in files.items() if n.startswith(prefix)}
assert len(payload) == 6, payload
for name in ['Check.cs', 'check.sh', 'README.md']:
    assert files[prefix + 'share/doc/dotnet-netcore-platforms212/' + name] == (Path('mingw-w64-dotnet-netcore-platforms212') / name).read_bytes()
report = dict(artifact=artifact.name, artifact_sha256=sha(artifact.read_bytes()),
              source_commit='6851cc781ad2ff33d4a0f429a6fc1ab85abaff86',
              source_archive_sha256=sha(source.read_bytes()), nupkg_sha256=sha(package),
              original_graph_sha256=sha(graph), runtime_ids=515,
              exact_original_source_graph_and_licenses=True,
              release_graph_equal_after_newline_normalization=True,
              contains_implementation_binaries=False, payload_sha256=payload,
              full_dependency_goal_complete=False)
output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
