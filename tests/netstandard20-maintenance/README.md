# Source netstandard2.0 maintenance dependencies

The [formal maintenance bundle](../../mingw-w64-dotnet-maintenance-netstandard/README.md)
now builds and installs this profile using the packaged compiler, reference pack
and IL assembler. It explicitly evaluates Release, preserves the original newer
framework inbox placeholders and checks both isolated Standard implementations
and source-framework selection. The records below describe the earlier private
bootstrap workflow; legacy Framework production variants remain a separate gate.

Five original implementations now build for their declared netstandard2.0
target and pass an isolated consumer: System.Buffers 4.6.1, System.Numerics.Vectors
4.6.1, System.Memory 4.6.2, System.Runtime.CompilerServices.Unsafe 6.1.1 and
System.Threading.Tasks.Extensions 4.6.2. Roslyn 4.14 selects these versions in
its original `DotNetBuildSourceOnly` configuration. These are private prerequisites
for the shipping generator dependency graph; no pacman installation is claimed.

The exact commits come from the publisher's text-only NuGet manifests, saved
under `inputs/*.publisher.nuspec`. No downloaded package binaries are build
inputs. The original C# and IL implementation sources are unchanged.

| Source | Commit | Archive SHA256 |
| --- | --- | --- |
| Four C# packages | `6b84308c9ad012f53240d72c1d716d7e42546483` | `5f8a5d6a7fe51c06216d21eb06fd2c4ad4bae2b4a3b13319a74d790919b7492c` |
| Unsafe 6.1.1 | `ab95a1f103b49919ba02577a99f3173405bb50ca` | `6e6f764834ebf0d9135d0c0dff9d78209df629eee496192c022a531e7f915a7e` |

MSBuild evaluates the original four C# projects for netstandard2.0. The private
wrappers retain their assembly versions, keys, source selections, resources and
dependency identities. Source versions differ from their deliberately frozen
assembly versions. The private file versions use the package version plus `.0`;
informational versions record the exact source commit.

Unsafe builds from its original IL using the
[source .NET 10 native IL assembler](../runtime10-ilasm/README.md).
Its generated `version.h` follows the original IL project target. A source SDK
versioning build supplies the native VERSIONINFO payload, preserved byte for byte
through LLVM resource tools into the IL image. All 42 original public Unsafe
methods remain present. Three original resource sets and all 19 strings match.

The consumer loads all five exact source assemblies in a separate load context.
It exercises Unsafe reference/pointer/unaligned operations, pool ownership and
clearing, overlapping spans, segmented Unicode sequences, UTF8 parsing/formatting,
endian primitives, vectors/matrices, async ValueTask builders, IValueTaskSource
completion and cancellation. All 1,108 original documented declarations resolve
to the intended assemblies: 1,012 public/protected declarations and 96 documented
implementation details. This documentation check is scoped to those declarations.

Audits verify 141 original source/project/resource inputs against both pinned
archives, every actual compiler/consumer package cache entry and every cached
DLL against the source feeds. A separate audit verifies the original XML
documentation baselines and build policies, plus every package's shipped license,
readme and documentation bytes. The final build uses a new compiler cache after
the license packaging correction; the final consumer starts with a fresh cache.
Recorded nonfatal warnings include original CLS diagnostics and NU1603 when the
original Platforms >=1.1.0 minimum selects the available source 1.1.2 package.

Copy this directory to `maintenance20-workflow` in the prepared Windows CLANG64
root. Place `maintenance-6b84308c.tar.gz` and `maintenance-ab95a1f1.tar.gz` beside
it. The preceding source SDK8, compiler adapter, netstandard20-2 reference feed
and corrected native IL assembler are prerequisites:

```sh
ROOT=/c/codex-dotnet10/c1.1BZ8KU
/usr/bin/python3 "$ROOT/maintenance20-workflow/prepare.py" "$ROOT" "$ROOT/maintenance20-1"
export MAINTENANCE_BOOTSTRAP_CACHE="$ROOT/maintenance20-1/cache3"
/usr/bin/python3 "$ROOT/maintenance20-workflow/build.py" "$ROOT" "$ROOT/maintenance20-1"
/usr/bin/python3 "$ROOT/maintenance20-workflow/check.py" "$ROOT" "$ROOT/maintenance20-1" "$ROOT/maintenance20-1/consumer2"
/usr/bin/python3 "$ROOT/maintenance20-workflow/audit-assets.py" "$ROOT" "$ROOT/maintenance20-1"
```

All recorded final commands returned zero. Preparation and consumer directories
must be new. `check.py --resume` explicitly reuses a prior consumer while still
performing the complete checks. `build.py` verifies original source hashes before
rebuilding an existing prepared output. Detailed results are in
[the JSON record](source-results-20261028.json) and
[the logs](source-results-20261028.txt).

The remaining original netstandard2.0 runtime9/Roslyn4.14/Workspaces variants,
Roslyn/Workspaces4.4 for JSON generation, the generator bundle and formal complete
package/install validation remain open. These private packages contain the
netstandard2.0 assets needed by this graph; other upstream package TFMs are not
claimed complete. The full PowerShell dependency objective remains active.

The subsequent [runtime9 netstandard2.0 build](../runtime9-netstandard/README.md)
uses these maintenance packages for eleven original implementations plus their
composition metapackage, closing the next generator-dependency prerequisite.
