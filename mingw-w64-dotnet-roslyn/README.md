# Roslyn 4.9.2 compiler libraries for .NET 8

Builds `Microsoft.CodeAnalysis.Common` and `Microsoft.CodeAnalysis.CSharp`
4.9.2 from the exact source commit named by the upstream NuGet package:
`9934fb9e3527e1c0c51314e57d4aab30f97e8f9e`. The source also declares 4.9.2.

Both libraries target net8.0 for this PowerShell/.NET 8 distribution. The
installed source-built runtime supplies Immutable, Reflection.Metadata and
Unsafe. The recipe does not download any NuGet implementation assemblies or
reuse the SDK's compiler DLLs as package payloads. The installed compiler is a
build tool for compiling the actual 4.9.2 sources.

Each NuGet package includes its 13 localized satellite assemblies, compiled
from the upstream XLF translations. The shared library includes both its main
compiler messages and the Collections strings. Satellite manifest names include
their culture suffix, as required by ResourceManager.

The three upstream syntax/bound-tree/error-facts generators are compiled and
run, resources are compiled from their upstream .resx text, and every upstream
friend-assembly declaration is preserved. Assemblies are public-signed with
the MicrosoftShared public key in the source, yielding the upstream
31bf3856ad364e35 identity and assembly version 4.9.0.0. File version 4.9.2.0 and
the source commit identify this rebuild; public signing is not an authentic
Microsoft private-key signature.

All five regenerated files must match their checked-in baselines after BOM,
line-ending and the console generator's specific blank-line cleanup. The
gate does not ignore arbitrary whitespace or source differences.

Run `makepkg --cleanbuild --force --noconfirm` in CLANG64 to build both split
packages. After installing both, run from a new directory/cache:

```bash
bash mingw-w64-dotnet-roslyn/check.sh /tmp/roslyn-installed-check
```

The consumer restores only from the installed feed and checks the actual
assembly locations, versions and signing identities. It parses C# 12 primary
constructors and collection expressions, checks semantic symbols, emits and
executes deterministic PE/portable PDB output, and verifies source documents and
sequence points. It checks error/nullable diagnostics, command-line options,
cancellation, AnalyzerFileReference loading, analyzer callbacks and incremental
generation with AdditionalText. All **10,299** tracked upstream public API
declarations are compared with imported metadata, including nullability,
constants, defaults and modifiers; upstream removal markers are applied.
All **35,750** strings in **39** localized resource sets are checked, including
an actual German diagnostic. Framework native helpers are rejected.

The API check uses the MIT-licensed PublicApiAnalyzers 3.3.4 display format:
https://github.com/dotnet/roslyn-analyzers/blob/v3.3.4/src/PublicApiAnalyzers/Core/Analyzers/DeclarePublicApiAnalyzer.cs
It verifies tracked declarations, rather than proving every custom attribute,
generic constraint, layout or binary-compatibility property.

The netstandard2.0/net6.0 assets, Visual Basic compiler, MSBuild tasks,
compiler-server executables and IDE workspaces are outside these two package
IDs. Microsoft.CodeAnalysis.Analyzers 3.3.4 is a separate outstanding build
dependency; Roslyn's own source-build configuration permits its exclusion
while building the compiler. Packaging it remains part of the overall
PowerShell dependency goal. Full PowerShell integration remains unproven.
Native Windows PDB/DIA behavior, edit-and-continue, remote analyzers, compiler
server integration and security auditing are not established by these checks.
