# Original SDK10 configuration and binding-generator bootstrap

Builds five original profiles from SDK-pinned runtime VMR44525024:
Microsoft.Extensions.Primitives,Configuration.Abstractions,Configuration and
Configuration.Binder target NET10. The binding generator retains its original
netstandard2.0 target and exact Roslyn4.8 CSharp.Workspaces dependency. All105
original C# inputs are retained unchanged. Default source globs are included
only for original projects that enable them; the generator enumerates its
source files explicitly. Direct/transitive project references and the
ReferenceOutputAssembly=false generator edge are preserved.

The build uses the verified runtime snapshot shared with sdk10-extensions.
The original Arcade resource/version tasks produce assembly10.0.0.0 and
file10.0.225.61305 under BuildID20251212.105. Original MicrosoftAspNetCore keys,
18 resource sets/260 exact strings,13 NS2 satellites and five portable PDBs pass.
Selected original source/resource/project/XLF inputs match the pinned VMR
archive; actual reference/output hashes are checked.

The runtime consumer exercises the original generator through source compiler5.3
against the four original NET10 libraries. Generated binding handles Unicode,
scalars,arrays,nested values,reloads and conversion errors. Consumer IL is
inspected to require calls into the generated interceptors. Consumer IL inspection proves that the generated interceptor path executes.

All299 checked CLR declarations match. Configuration.Abstractions,Configuration
and Binder also match nullable metadata. The strict Primitives comparison FAILS
with one original-source discrepancy: StringValues implements
IEquatable<string?[]?> while its pinned reference declares IEquatable<string?[]>.
The full report is retained without changing either production declaration.
Strict nullable parity remains open.

The package supplies four NET10 NuGet archives and the Binder generator under
its original analyzers/dotnet/cs layout, including all original NS2 satellites.
Binder's checked-in buildTransitive target is copied byte-for-byte. Staged and
installed checks execute its opt-in/removal behavior,interceptor namespace setup
and unsupported-framework warning. Production builds use installed source
Roslyn4.8 archives. The earlier private prototype's inputs are retained in the
prototype evidence. Other original framework profiles,complete upstream/analyzer
integration and the logging/console/SDK10/PowerShell7.6 graph remain required.
The strict StringValues nullable-interface gate stays failed and visible.

Clean makepkg,archive audit,installed offline restore/runtime/targets and package integrity passed on win11 on2026-10-29. Pacman reports130 files/0 altered;older Primitives6 reports13 files/0 altered. The original strict StringValues nullable gate remains FAILED and visible. [Commands and evidence](package-results-20261029.txt), [archive provenance](package-artifact-20261029.json).
