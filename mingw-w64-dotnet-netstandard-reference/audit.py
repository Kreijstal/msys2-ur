"""Audit package metadata, original packaging inputs and actual restored bytes."""
from pathlib import Path
import hashlib
import json
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

archive, out, consumer, feed = (Path(p).resolve() for p in sys.argv[1:])
here = Path(__file__).resolve().parent
source = out / 'standard-18a36291e48808fa7ef2d00a764ceb1ec95645a5'
sha = lambda data: hashlib.sha256(data).hexdigest()
assert sha(archive.read_bytes()) == '754ee66a33122c6c5c45fe75d060f9131c6b16a23af315c8c063a54fbc911e7c'
publisher = here / 'inputs/NETStandard.Library.publisher.nuspec'
assert sha(publisher.read_bytes()) == 'f0c9c450d3c84f9c6c2728834843731a09e259d3aa784b65a557fbd370d73d77'
ns = {'n': 'http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd'}
def groups(tree):
    return {g.get('targetFramework'): {d.get('id'): d.get('version') for d in g}
            for g in tree.findall('.//n:dependencies/n:group', ns)}
expected = groups(E.parse(publisher))
assert len(expected) == 20 and sum(map(len, expected.values())) == 337
package = feed / 'netstandard.library.2.0.3.nupkg'
metadata = json.loads((out / 'package-metadata.json').read_text())
with zipfile.ZipFile(package) as z:
    assert len(z.namelist()) == len(set(z.namelist()))
    assert set(z.namelist()) == set(metadata['package_files_sha256'])
    assert groups(E.fromstring(z.read('NETStandard.Library.nuspec'))) == expected
    assert z.read('LICENSE.TXT') == (source / 'LICENSE.TXT').read_bytes()
    assert z.read('lib/netstandard1.0/_._') == b''
    for name, digest in metadata['package_files_sha256'].items():
        assert sha(z.read(name)) == digest, name
        if name.endswith('.dll'):
            assert z.read(name) == (out / 'ref' / Path(name).name).read_bytes()
    cache = consumer / 'cache/netstandard.library/2.0.3'
    assert (cache / package.name).read_bytes() == package.read_bytes()
    for name in z.namelist():
        assert (cache / name).read_bytes() == z.read(name), name
wanted = {name: sha((source / name).read_bytes()) for name in (
    'LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT', 'BuildToolsVersion.txt', 'netstandard/pkg/NETStandard.Library.pkgproj',
    'netstandard/pkg/NETStandard.Library.dependencies.props',
    'netstandard/pkg/targets/netstandard/NETStandard.Library.targets',
    'pkg/baseline/packageIndex.json', 'netstandard/pkg/shims/dir.targets')}
verified = set()
with tarfile.open(archive) as t:
    assert t.pax_headers['comment'] == '18a36291e48808fa7ef2d00a764ceb1ec95645a5'
    for m in t:
        name = m.name.partition('/')[2]
        if m.isfile() and name in wanted:
            assert sha(t.extractfile(m).read()) == wanted[name]
            verified.add(name)
assert verified == set(wanted)
runtime_metadata = json.loads((consumer/'metadata-results.json').read_text())
assert runtime_metadata['runtime_facades_loaded'] == 112
assert runtime_metadata['original_cls_compliant_defaults_verified'] == 117
assert runtime_metadata['reference_contract_runtime_rejected']
if feed == Path('/clang64/lib/dotnet/library-packs'):
    installed = Path('/clang64/lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0')
    refs = sorted((out / 'ref').glob('*.dll'))
    assert len(refs) == 113 and {p.name for p in refs} == {p.name for p in installed.glob('*.dll')}
    for p in refs:
        assert (installed / p.name).read_bytes() == p.read_bytes(), p.name
report = dict(original_dependency_groups_verified=20, original_dependency_edges_verified=337,
              original_unique_dependency_versions_verified=44, original_packaging_archive_inputs_verified=8,
              runtime_facades_loaded=112, original_facade_marker_and_file_version_policy_verified=True,
              package_sha256=sha(package.read_bytes()), all_restored_files_match_package=True,
              installed_reference_pack_verified=feed == Path('/clang64/lib/dotnet/library-packs'),
              older_framework_dependency_runtime_closure_verified=False,
              full_dependency_goal_complete=False)
(consumer / 'package-audit.json').write_text(json.dumps(report, indent=2) + '\n')
print('PASS full original dependency groups, source packaging inputs, package and restored reference bytes')
