# PolySharp1.15 source package

Latest: the clean pacman build, final archive audit and fresh installed checks
passed for 1.15.0-1. Pacman reports22 files and zero alterations; all268 previous
source-feed archives are unchanged. [Exact commands and results](package-results-20261031.txt).

Pinned original source02753db24d9685e54db06739eb63183d86eb5b62. The original
netstandard2.0 generator and NoTargets package projects build with source
SDK8.0.131/compiler5.0 bootstrap hosts, exact source Roslyn4.3.1 libraries,
ReproducibleBuilds1.2.25 and NoTargets2.0.1. The upstream release SDK is9.0.100;
that host has not been replayed. Auxiliary SDK queries from the original
global.json directory report that9.0.100 is unavailable; the explicit bootstrap
build completes with zero warnings/errors. No project profile is retargeted.

Five C# files have explicit style ports recorded by ports.py/source-ports.json:
collection expressions and expression-bodied operators. No warning suppressions
are added. Original Lang13/nullable/strict/warnings-as-errors and style analysis
remain enabled. Every original file is byte-verified, with separate before/after
hashes for the five edited files. All56 embedded source resources are unchanged
and remain both compiled input and embedded resources. The original generated
module attribute, assembly target/version and embedded portable PDB are checked.

Actual source Roslyn4.3 runs the generator against original NS2 references,
produces32 polyfills, emits and executes records/required members/range behavior.
A negative control fails without generation. The C#7 early-return paths produce
no generated trees or generator failures. Fresh NS2/NET8 NuGet consumers use the
original package targets and analyzer; NET8 execution passes.

The original compiler/legacy-project guards, missing-compiler behavior and
compiler-visible property normalization now pass in producer and installed
checks. The old compiler rejection uses a metadata fixture; it does not claim
execution of an old compiler. Broader upstream target profiles remain open.
Original upstream test projects declare System.Memory4.5.5 for older targets;
that exact test dependency has not been ported here. The full PowerShell
dependency goal remains open.
