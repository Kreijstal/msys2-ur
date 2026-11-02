# Original source .NET Standard 2.1 reference pack

Builds the complete 121-assembly Standard2.1 reference pack from the original
dotnet/standard v2.1.0 commit `a5b5f2e1e369972c8ff1e2183979fab6099f52ef`.
The four additional extension assemblies required by the original project graph
are compiled for validation but are not installed as part of the reference pack.
Production source files are unchanged; executable binary inputs are removed.

The installed source Compiler5 bootstrap compiles the original explicit Compile
and ProjectReference graph with no standard-library references. Original keys
come from the exact Arcade commit declared by the Standard source manifest.
Assembly identities, CLS policy, framework metadata, original type forwards,
and file versions are checked independently. File versions use the original
Arcade task with the source commit's UTC date and revision 1, rather than a
vendor binary build number. Informational versions identify the source commit.

The check compares every producer input against the original source archive,
checks the complete metadata/forward graph, executes the original Arcade
version task and three original test vectors, then builds a fresh SDK8
netstandard2.1 consumer from these exact references. The consumer uses Span,
ranges, async enumeration/disposal and Unicode and executes on the source-built
NET8 runtime. A negative control rejects a newer API outside this contract.

This pack enables the original AsyncInterfaces netstandard2.1 forwarder. It
does not complete the remaining runtime9 variants, Roslyn packages, runtime10
generator bundle, SDK/desktop10 or PowerShell7.6 integration.
