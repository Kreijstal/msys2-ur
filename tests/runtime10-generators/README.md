# Original .NET10 targeting-pack generators

All six original generator assemblies and 65 satellites are now formally
packaged and installed as `mingw-w64-clang-x86_64-dotnet-runtime10-generators
10.0.5-1`. The clean package build, actual installed-generator consumer,
source/cache audits and full installed-byte/reference-input audits all pass.
The bundle validates all eight generator entry points, ten analyzers, seven
codefix providers and 71 resource sets / 12,383 values. It uses installed source
Roslyn4.14/4.4 and all 167 installed source NET10 contracts, and rebuilds JSON10
NET8 execution fixtures from source. These fixtures are not shipped.
Exact commands, warnings, limits and results are in
[package-results-20261028.txt](package-results-20261028.txt) and
[package-results-20261028.json](package-results-20261028.json).
Formal JSON runtime packages, remaining target variants, final SDK targeting-pack
integration, full framework/SDK/desktop10, PowerShell7.6 and all remaining
compatibility gates remain open.

The original NET8 JSON/encoder/pipelines runtime profile is now also formally
packaged; see [../json10-net8/README.md](../json10-net8/README.md). Other original
runtime target variants and source ILLink/metadata/trimming gates remain open.

The following records the earlier private bootstrap and its historical status.

All six generators named by the original NetCoreAppLibraryGenerator manifest
now build from unchanged .NET10.0.5 production C# sources for netstandard2.0:
Microsoft.Interop.SourceGeneration, LibraryImport, COM, JavaScript import/export,
JSON and Regex. The eight actual generator entry points, ten analyzers and
seven code-fix providers match every corresponding declaration in the original
active sources. These are private source artifacts; formal pacman packaging,
clean/installed gates and complete SDK integration remain open.

Runtime source commit: `081d220c0a773ffb7c6bea6b48727833576a65ef`.
Archive SHA256: `1692acae5e3adfd625452fbc9db4fd4e982c10e38189358ae245c74dd5514d7a`.
The generators use the complete source Roslyn4.14 dependency graph and the
original Roslyn4.4 CSharp.Workspaces graph for JSON. All309 original C# inputs,
original conditional nullable/platform/obsolete/index policies, new .NETStandard
exception/caller-argument polyfills, signing identities and resources are retained.
MSBuild evaluates the original projects and shared source policies in Release.

Validation runs all eight generators against all167 original public .NET10
reference assemblies and emits their generated C# as real assemblies. Cases
cover native LibraryImport, COM interfaces/classes, vtable-index stubs using the
original ancillary test APIs, JavaScript import/export, JSON and Regex. Native
GetCurrentProcessId, JSON serialization/deserialization including Unicode names,
and Regex matches/non-matches execute on the source .NET8 host. JSON10-generated
output requires actual JSON10 metadata APIs, so the original JSON10 implementation
and its encoder/pipelines dependencies were built for their declared supported
net8.0 target: all346/26/33 original source inputs remain unchanged. This is a
JSON10 implementation running on .NET8, rather than execution against JSON8.
Full .NET10 framework execution and browser/COM runtime integration remain open.

The unchanged source Compiler5 adapter originally resolved framework Immutable8;
the new generators require Immutable9. prepare-host.py creates a separate host
with explicit exact source Immutable9/Metadata9 dependencies. Compiler5, its
command-line implementation and its adapter DLL bytes are unchanged. The old
host and installed SDK remain untouched. JSON10 builds with the original Regex10
generator using this host. The original three JSON runtime dependency projects
and all generated Regex sources are audited.

All71 generator resource sets /12,383 values, assembly identities, original
source attributes and framework targets pass. All ten analyzers run without
AD0001; import/regex recommendations and invalid generator inputs produce their
original diagnostics. All seven codefix providers activate; the real Regex
codefix action applies and the resulting generated code compiles. Source audits
verify331 generator source/resource/policy inputs,177 actual package references,
every cached package/DLL, all405 original JSON/encoder/pipelines C# inputs and
413 corresponding archive inputs, exact peer references and source compiler-host
dependency bytes. These checks do not establish complete attribute metadata or
full runtime parity outside the explicit tested cases.

The reviewable source bundle contains six main DLLs,65 satellites and both
original license/notices files, with a manifest of exact bytes:73 files total.
It follows the analyzer directory layout and does not include Roslyn runtime
DLLs as replacement framework assets. Installed SDK integration and packaging
must still supply a host meeting the actual original compiler requirements.
Bundle: `/tmp/runtime10-generators1/runtime10-generators-source-bundle1.tar.gz`,
SHA256 `f8ecaf995d3b58b3693b54487f247b70d536e2ea0342bc3d0484fa8a826bd229`.

Copy this directory into runtime10-generators-workflow1 in the prepared CLANG64
root. The preceding pinned runtime source, source dependency feeds, reference10-2
contracts and source Compiler5 adapter are prerequisites. Output directories must
be new. The exact successful commands (including prepare-host.py, prepare-json8.py,
build-json8.sh, check.py, both auditors and stage.py) are in
[source-results-20261028.txt](source-results-20261028.txt), with structured data
in [source-results-20261028.json](source-results-20261028.json).
All12 tested workflow files match the repository copies byte for byte.

Evidence: `/tmp/runtime10-generators1/runtime10-generators-evidence1.tar.gz`,
SHA256 `3bff920678bfa0914225958380d8337cfee64393875969f3ebb7dc86f17f845a`.
The broader PowerShell dependency goal remains incomplete. No installed package
or package-catalog artifact count changed.
