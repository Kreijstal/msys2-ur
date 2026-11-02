# Original .NET10 reference contracts

Builds the complete declared public reference graph from runtime10.0.5 source:
167 public assemblies and 19 private facade stubs. Only the public reference
assemblies ship, under `lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0`.
The stubs provide private compiler inputs and no runtime implementations.

Actual source SDK MSBuild evaluates all original projects and emits stub sources
through the original target. All selected source/project/property files must
match the pinned runtime archive. The exact Arcade revision mapped by the
original VMR manifest supplies version calculation and facade-reference version
clearing; its archived files must match the included original task sources.
The installed source compiler5 builds references with nostdlib/refonly and their
original dependency closure. No binary .NET10 targeting pack is used. Metadata,
identities, keys, versions and dependencies are checked for the entire graph.
A C#14/.NET10 API consumer compiles with all 167 contracts and must fail against
the installed NET8 contracts with missing Sequence/AsyncEnumerable diagnostics.
This is a compile check; runtime10 execution requires the matching framework.

Run `python make-source.py`, then Windows CLANG64:
`MINGW_ARCH=clang64 makepkg-mingw -C -f --noconfirm`.
The formal generator bundle, final SDK targeting-pack layout/integration,
complete managed/native framework, SDK/desktop10, PowerShell7.6 and remaining
compatibility gates remain open parts of the full dependency goal.
