#!/usr/bin/env python3
"""Export only source inputs for the serviced targeting pack build."""
from pathlib import Path
import gzip
import hashlib
import io
import sys
import tarfile

package = Path(__file__).resolve().parent
# Workflow sources live in https://github.com/Kreijstal/dotnet-mingw-bootstrap
# (workflows/); pass its checkout, default ../../dotnet-mingw-bootstrap.
bootstrap = Path(sys.argv[1]) if len(sys.argv) > 1 else package.parent.parent / 'dotnet-mingw-bootstrap'
source = bootstrap / 'workflows/runtime-servicing'
names = [
    'source-inputs.json', 'prepare.py', 'prepare-version.py',
    'inputs/CalculateAssemblyAndFileVersions.cs', 'inputs/Arcade-LICENSE.TXT',
    'prepare-file-version.py', 'prepare-framework.py', 'build-framework.sh',
    'audit-framework.py', 'prepare-managed.py', 'prepare-targeting-generators.py',
    'prepare-targeting-common.py', 'build-targeting-generators.sh',
    'inspect-targeting-generators.sh', 'audit-targeting-generators.py',
    'stage-targeting-pack.py', 'complete-targeting-manifest.py',
    'collect-targeting-licenses.py', 'build-targeting-pack.sh', 'check-sdk.sh',
    'check-targeting-pack.sh', 'check-targeting-generators.sh', 'SdkGeneratorCheck.cs',
    'clear-forwarder-versions.py', 'audit-shim-identities.py',
    'inputs/GenFacades-BuildTask.cs', 'inputs/ClearAssemblyReferenceVersions.cs',
    'inputs/GenFacades.ClearVersion.targets',
]
files = [(source / name, name) for name in names]
files += [(p, p.relative_to(source).as_posix()) for p in sorted((source / 'patches').glob('*.patch'))]
files += [(p, p.relative_to(source).as_posix()) for p in sorted((source / 'targeting-inputs').iterdir()) if p.is_file()]
files.append((package.parent / 'mingw-w64-dotnet-system-text-json8/InspectAssemblyMetadata.cs', 'InspectAssemblyMetadata.cs'))
files.append((package / 'check-installed.sh', 'check-targeting-installed.sh'))
assert len(files) == 54, len(files)
destination = package / 'dotnet-targeting8-servicing-source-2.tar.gz'
with destination.open('wb') as stream, gzip.GzipFile(filename='', fileobj=stream, mode='wb', mtime=0) as compressed:
    with tarfile.open(fileobj=compressed, mode='w', format=tarfile.GNU_FORMAT) as tar:
        for file, relative in sorted(files, key=lambda pair: pair[1]):
            data = file.read_bytes()
            entry = tarfile.TarInfo('servicing/' + relative)
            entry.size = len(data)
            entry.mode = 0o755 if file.suffix == '.sh' else 0o644
            tar.addfile(entry, io.BytesIO(data))
print(destination)
print(hashlib.sha256(destination.read_bytes()).hexdigest())
