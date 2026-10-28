#!/usr/bin/env python3
"""Export the checked-in servicing workflow as a deterministic source archive."""
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
files = [source / name for name in [
    'README.md', 'source-inputs.json', 'prepare.py', 'build-all.sh',
    'build-native.sh', 'prepare-managed.py', 'build-generators.sh',
    'prepare-corelib.py', 'build-corelib.sh', 'prepare-framework.py',
    'build-framework.sh', 'build-compression.sh', 'audit-build.py',
    'audit-framework.py', 'stage-runtime.py', 'build-runtime-check.sh',
    'check-runtime.sh', 'RuntimeCheck.cs', 'check-powershell.sh', 'PowerShellCheck.ps1',
    'prepare-version.py', 'prepare-file-version.py', 'check-json-binding.sh',
    'inputs/CalculateAssemblyAndFileVersions.cs', 'inputs/Arcade-LICENSE.TXT',
    'clear-forwarder-versions.py', 'audit-shim-identities.py',
    'inputs/GenFacades-BuildTask.cs', 'inputs/ClearAssemblyReferenceVersions.cs',
    'inputs/GenFacades.ClearVersion.targets', 'check-framework-forwarders.sh',
    'FrameworkForwarderCheck.cs',
]] + sorted((source / 'patches').glob('*.patch'))
assert len(files) == 49
destination = package / 'dotnet-runtime8-servicing-source-3.tar.gz'
with destination.open('wb') as stream, gzip.GzipFile(filename='', fileobj=stream, mode='wb', mtime=0) as compressed:
    with tarfile.open(fileobj=compressed, mode='w', format=tarfile.GNU_FORMAT) as tar:
        for file in sorted(files):
            data = file.read_bytes()
            entry = tarfile.TarInfo('servicing/' + file.relative_to(source).as_posix())
            entry.size = len(data)
            entry.mode = 0o755 if file.suffix == '.sh' else 0o644
            tar.addfile(entry, io.BytesIO(data))
print(destination)
print(hashlib.sha256(destination.read_bytes()).hexdigest())
