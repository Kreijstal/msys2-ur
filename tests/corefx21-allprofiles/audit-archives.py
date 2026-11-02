"""Verify original package profiles, aliases, XML data and dependency groups."""
from pathlib import Path
import hashlib
import json
import sys
import urllib.parse
import xml.etree.ElementTree as E
import zipfile

originals, producer, archives, output = (Path(p).resolve() for p in sys.argv[1:])
results = {}
for name, version in [('System.Collections.Immutable', '1.5.0'), ('System.Reflection.Metadata', '1.6.0')]:
    original = originals / (name.lower() + '.' + version + '.metadata-only.nupkg')
    candidate = archives / 'feed' / (name + '.' + version + '.nupkg')
    with zipfile.ZipFile(original) as before, zipfile.ZipFile(candidate) as after:
        want = {n for n in before.namelist() if n.startswith('lib/')}
        actual = {n for n in after.namelist() if n.startswith('lib/')}
        assert actual == want, (name, 'original lib assets', actual ^ want)
        for path in want:
            if path.endswith('.xml'): assert after.read(path) == before.read(path), path
            elif path.endswith('.dll'):
                framework = path.split('/')[1]
                if framework.startswith('portable-'): framework = 'netstandard1.0' if name.endswith('Immutable') else 'netstandard1.1'
                source = producer / name / framework / 'bin/Release' / (name + '.dll')
                assert after.read(path) == source.read_bytes(), path
            else: raise AssertionError(path)
        for filename in ['LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT', 'version.txt', 'useSharedDesignerContext.txt']:
            assert after.read(filename) == before.read(filename), (name, filename)
        def dependencies(z):
            tree = E.fromstring(z.read(next(n for n in z.namelist() if n.endswith('.nuspec'))))
            return [(g.get('targetFramework'), [d.attrib for d in g]) for g in tree.findall('.//{*}dependencies/{*}group')]
        assert dependencies(after) == dependencies(before), (name, 'dependency groups')
        assert not any(n.startswith('ref/') or n.endswith('.pdb') for n in after.namelist())
        results[name] = dict(version=version, archive_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
            original_DLL_XML_paths=sorted(want), original_dependency_groups=dependencies(after), original_portable_byte_aliases=True,
            XML_and_license_version_designer_data_byte_identical=True)
        print('PASS original DLL/XML paths, portable alias, dependency groups and data assets:', name)
output.write_text(json.dumps(dict(packages=results, full_dependency_goal_complete=False), indent=2) + '\n')
