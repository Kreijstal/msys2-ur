# Source SolutionPersistence 1.0.52

Builds the original NET8 source-only profile required by SDK10's MSBuild18.3,
from publisher-pinned commit19c3ca7dc997dba2b3a86f6c666e9f717f34c8fe.
The original project, checked-in resource designer and resource data are used.
SourceBuild=true disables original development-only analyzer/versioning package
dependencies. The SDK source-build version is set explicitly to1.0.52.
Source SDK8/MSBuild and the installed source NET10 CSharp13 compiler perform
the build. Runtime and reference inputs come from installed source packages.

The source NuGet contains the original net8.0 asset, consumed from a fresh
isolated source-only restore. Checks cover the original public API declarations,
SLN/SLNX Unicode model roundtrips, five original serializer vectors, invalid XML
and SLN read cancellation. The unchanged original XML reader completes with a
pre-canceled token; XML cancellation is not supported by that reader. Actual
original selected compiler/resource bytes and the
producer/consumer NuGet/DLL bytes are audited. Production source changes:0.

The original net472 profile and its dependencies, full MSBuild18.3/SDK10,
WindowsDesktop10, PowerShell7.6 and other dependency/compatibility gates remain
unfinished. Source package readme advisories and original warnings remain visible.
