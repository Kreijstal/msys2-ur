# Original runtime9 netstandard2.0 generator dependencies

The [formal runtime9 library component](../../mingw-w64-dotnet-runtime9-libraries/README.md)
now builds this graph using installed source prerequisites and also supplies the
five original NET8 MEF targets. Revision2 also ships the genuine AsyncInterfaces
Standard2.1 forwarding target and its empty dependency group; fresh installed
NET8 consumers verify source bytes, all forwards and shared async type identity.
See [revision2 package results](package2-results-20261028.txt). It evaluates
Release explicitly and checks the original assembly policies. The records below
describe the preceding private bootstrap; other required framework variants and
the full newer-framework dependency closure remain incomplete.

This private workflow builds eleven original runtime9 library implementations
for netstandard2.0 plus the original System.Composition dependency metapackage.
They supply the older target-framework variants needed by the Roslyn4.14 and
.NET10 shipping-generator graph. These are private prerequisites; formal package
installation and the complete PowerShell dependency objective remain open.

The libraries are Collections.Immutable, Reflection.Metadata, all five
Composition components, Microsoft.Bcl.AsyncInterfaces, IO.Pipelines,
Threading.Channels and Text.Encoding.CodePages, all version9.0.0. Sources are
pinned to runtime commit `9d5a6a9aa463d6d10b0b0ba6d5982cc82f363dc3`, archive SHA256
`32755d528ead386762fb9da054249f6151ac78ef6a92f437044838cd0ab00def`.
No production C# inputs are edited.

The workflow reuses the binary-clean source extraction from
[`../runtime10-generator-deps`](../runtime10-generator-deps/README.md).
MSBuild evaluates the original projects and conditions for netstandard2.0.
The relevant original shared-source policies retain nullable, platform,
obsolete and index/range compatibility definitions. The original LibraryImport
configuration file supplies its compiler-visible properties. All library
compilations record their actual sources, references, analyzers and generated
interop output.

Metadata's original source needs a generated native ReadFile wrapper. To break
the build dependency cycle, the two complete original runtime9 interop-generator
projects build first as private net8 tools. They use the installed source
Roslyn/Workspaces4.9.2, satisfying the original generator's4.8 minimum, with their
actual dependency identities retained. The libraries then compile with source
Roslyn5 against the source-built .NET Standard contract and
[maintenance dependencies](../netstandard20-maintenance/README.md).
The latter satisfy the original runtime9 minimum versions; the private NuGets
declare the exact resolved versions rather than relabeling implementations.
These bootstrap generator tools are separate from the still-required complete
shipping generator bundle and its declared dependencies.

The consumer targets netstandard2.0 and loads all eleven exact assemblies in a
separate load context. Checks cover immutable/frozen collections, real PE file
reading, metadata type-name parsing, MEF shared imports/exports, async iterator
completion/early disposal/cancellation, Unicode pipes and pending-read
cancellation, channel backpressure/cancellation/multiwriter/error identity, and
code-page round trips, incremental decoding and strict fallback behavior.
The original generated ReadFile function is also invoked directly with a real
file handle. Every original `codepages.nlp` byte and all neutral/localized
resource values are checked.

The API gate compares 4,051 public/protected declarations. Five libraries use
their independently selected original reference-project sources; AsyncInterfaces
uses its complete original sources; the five MEF libraries use the previously
verified source-net8 variants. It checks declaration identities, accessibility
and the recorded return/ref/readonly/accessor/field/constant shapes. Complete
attribute and formal package metadata validation remain additional packaging
gates. The source/archive and cache audit verifies the twelve package graphs,
original API inputs, resources/licenses, generated files and every actual
compiler/consumer package archive and cached DLL against source feeds.

Copy this directory to `runtime9-ns20-workflow` in the prepared Windows CLANG64
runtime root. The preceding source SDK8, compiler adapter, source net8 Roslyn
and runtime9 feeds, .NET Standard reference feed and maintenance feed are needed.
Preparation and consumer directories must be new:

```sh
ROOT=/c/codex-dotnet10/c1.1BZ8KU
/usr/bin/python3 "$ROOT/runtime9-ns20-workflow/prepare.py" "$ROOT" "$ROOT/runtime9-ns20-2"
export RUNTIME9_NS20_CACHE="$ROOT/runtime9-ns20-2/cache-final"
bash "$ROOT/runtime9-ns20-workflow/build.sh" "$ROOT/runtime9-ns20-2"
/usr/bin/python3 "$ROOT/runtime9-ns20-workflow/check.py" "$ROOT" "$ROOT/runtime9-ns20-2" "$ROOT/runtime9-ns20-2/consumer2"
/usr/bin/python3 "$ROOT/runtime9-ns20-workflow/audit.py" "$ROOT" "$ROOT/runtime9-ns20-2" "$ROOT/runtime9-ns20-2/consumer2"
```

`refresh-generator-config.py` verifies unchanged source hashes before refreshing
the original configuration import in an already prepared private output.
`check.py --resume` explicitly reuses a consumer. Final build and consumer caches
must remain aligned with the final feed artifacts after packaging changes.

Detailed final results and commands are recorded in
[`source-results-20261028.json`](source-results-20261028.json) and
[`source-results-20261028.txt`](source-results-20261028.txt).
All four recorded final commands returned zero. The source audit verifies730
original inputs and97 actual compiler/consumer package references. Runtime checks
preserve9 resource sets/375 strings and both original generated interop outputs.
Roslyn/Workspaces4.14 netstandard2.0, the original4.4 JSON-generator dependency
closure, the complete runtime10 generator bundle, formal clean package/metadata/
license/installed checks, framework/SDK/desktop10 and PowerShell7.6 remain open.
The established PowerShell dependency artifact counts are unchanged.

The subsequent [Roslyn4.14](../roslyn414-netstandard/README.md) and
[Workspaces4.14](../workspaces414-netstandard/README.md) netstandard2.0 variants
now use this graph and pass their source, consumer, API and resource checks.
Latest revision: runtime9 source libraries9.0.0-3 now build cleanly and are
installed. The package keeps exact producer references and publishes compatible
maintenance minimums. Both original and newer source-build maintenance selections
pass installed API/native/resource/cache checks with NU1608 treated as an error.
The genuine NET8 MEF and Standard2.1 forwarding targets remain verified.
Exact commands and603 verified evidence files are recorded in
[`package3-results-20261029.txt`](package3-results-20261029.txt).

