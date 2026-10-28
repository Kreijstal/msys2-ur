#!/usr/bin/env python3
"""Export the checked-in SDK servicing workflow as a deterministic source archive."""
from pathlib import Path
import gzip
import hashlib
import io
import sys
import tarfile

package = Path(__file__).resolve().parent
# Workflow sources live in https://github.com/Kreijstal/dotnet-mingw-bootstrap
# (workflows/); pass its checkout, default ../../dotnet-mingw-bootstrap.
# dotnet-sdk8-servicing-source-2.tar.gz is commit 4be2582's workflow.
bootstrap = Path(sys.argv[1]) if len(sys.argv) > 1 else package.parent.parent / 'dotnet-mingw-bootstrap'
source = bootstrap / 'workflows/sdk8-servicing'
names = [
    'build-host.sh', 'stage-sdk.py', 'prepare-check-layout.py', 'check-packs.sh',
    'audit-packs-check.py', 'inputs/BuildTask.cs', 'inputs/CreateFrameworkListFile.cs',
    'inputs/FileUtilities.cs', 'inputs/LICENSE.TXT', 'inputs/sharedfx.targets',
    'inputs/source-inputs.json',
]
destination = package / 'dotnet-sdk8-servicing-source-2.tar.gz'
with destination.open('wb') as stream, gzip.GzipFile(filename='', fileobj=stream, mode='wb', mtime=0) as compressed:
    with tarfile.open(fileobj=compressed, mode='w', format=tarfile.USTAR_FORMAT) as tar:
        for name in names:
            data = (source / name).read_bytes()
            entry = tarfile.TarInfo('sdk-servicing/' + name)
            entry.size = len(data)
            entry.mode = 0o644
            tar.addfile(entry, io.BytesIO(data))
print(destination)
print(hashlib.sha256(destination.read_bytes()).hexdigest())
