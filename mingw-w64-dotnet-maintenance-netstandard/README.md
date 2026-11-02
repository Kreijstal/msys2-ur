# Source maintenance primitives for .NET Standard

This bundle supplies the original .NET Standard 2.0 implementations required by
the Roslyn and runtime9 generator dependency graph. Bundle version20261028 names
the packaging snapshot; the NuGets retain their original individual versions:

| Package | NuGet version |
| --- | --- |
| System.Buffers | 4.6.1 |
| System.Numerics.Vectors | 4.6.1 |
| System.Memory | 4.6.2 |
| System.Runtime.CompilerServices.Unsafe | 6.1.1 |
| System.Threading.Tasks.Extensions | 4.6.2 |

The C# packages use maintenance-packages commit
`6b84308c9ad012f53240d72c1d716d7e42546483`; Unsafe uses
`ab95a1f103b49919ba02577a99f3173405bb50ca`. Both source archive hashes, original
text-only publisher manifests and version/source mappings are pinned. No
publisher binaries or private build outputs are inputs. The recipe uses the
declared installed source SDK8, Compiler5 host, .NET Standard reference pack,
native ILAsm10 and LLVM resource tools. Reference-pack revision3 or newer is
required so the original CLS-compliance metadata is retained. Its MSBuild evaluator builds locally.

The four C# projects are evaluated and compiled in Release, retaining original
source conditions, frozen assembly versions, keys, resources, CLS/default alias,
DLL search paths, inbox/serviceable and neutral-language policies. Unsafe builds
from unchanged original IL, retaining its native VERSIONINFO payload. The package
file versions identify these source builds; informational versions record commits.

Each NuGet preserves its original .NET Standard 2.0 dependency group and two
newer-framework inbox groups with their original placeholder layout. On .NET8,
the latter select framework implementations. The .NET Framework4.6.2 production
assets are not included in this component and remain a separate packaging gate.
This bundle does not claim the complete upstream multi-target packages.

Checks restore into empty caches using source feeds only. An isolated consumer
loads and executes all five .NET Standard implementations, checking their
identities, versions, keys, original resources, 1,108 documented declarations,
Unsafe operations, pool ownership/clearing, overlapping spans, segmented Unicode,
UTF8/endian primitives, vectors/matrices and ValueTask completion/cancellation.
The API checker uses the declared installed source Roslyn4.9.2; this validation
tool is separate from the still-required Roslyn4.14 shipping dependencies.
A second consumer verifies .NET8 inbox selection through actual compiler
reference paths, selected NuGet assets and runtime type locations. Audits compare
all original selected inputs with pinned archives and every actual package cache
and cached DLL with its source feed, including the shipped text assets.

Run `python make-source.py`, then in Windows CLANG64 run
`MINGW_ARCH=clang64 makepkg-mingw -C -f --noconfirm`.
After installing, use `check.py ARCHIVE_DIRECTORY PREPARED NEW_CONSUMER
/clang64/lib/dotnet/library-packs` and
`check-inbox.py PREPARED NEW_INBOX_CONSUMER /clang64/lib/dotnet/library-packs`
to verify fresh installed-feed consumers. The payload contains five NuGets,
documentation and notices; it does not overwrite framework implementation DLLs.

Remaining work includes the runtime9 and Roslyn source generator dependency
packages, complete shipping generators, runtime/SDK/desktop10, PowerShell7.6,
legacy framework variants and the other open compatibility gates. The full
PowerShell dependency goal remains active.
