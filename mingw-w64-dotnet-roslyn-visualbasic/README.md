# Source-built Roslyn Visual Basic 4.9.2

This package supplies the complete `Microsoft.CodeAnalysis.VisualBasic` 4.9.2
compiler library for .NET 8, a prerequisite for the full Visual Basic analyzer
and code-fix payload of Microsoft.CodeAnalysis.Analyzers. It references the
separately source-built Microsoft.CodeAnalysis.Common 4.9.2 package. It does not
replace the installed SDK's compiler or supply the vbc/VBCSCompiler command-line
hosts, Visual Basic Workspaces, Features or IDE components.

Source is Roslyn commit `9934fb9e3527e1c0c51314e57d4aab30f97e8f9e`, archive SHA256
`e01ea67aaec6408de51a0a4c18a7e15b2a527ca7a853c9a0a7742cb5680aeb30`.
The installed source-built SDK's VB compiler bootstraps the original syntax and
error-facts generators. The original C# BoundTreeGenerator is also rebuilt.
All five generated VB source files and the grammar match the pinned baseline
when comparing UTF-8 text and line endings. No checked-in compiler binary or
published implementation is used as a build input.

The library compiles all 905 original non-generated source inputs, including the
shared BasicAnalyzerDriver, plus five regenerated files. It preserves upstream
VBRuntime=Embed, empty RootNamespace, global imports, friend declarations and
four embedded VB source templates. The upstream SDK workaround removes normal
VB runtime references after ResolveTargetingPackAssets, so embedded support is
used consistently. Unchecked integer arithmetic is required for the compiler's
internal bitmask/CRC constants. It does not override user-compilation overflow
choices: emitted checked and unchecked arithmetic are both tested explicitly.
Six upstream ByRef/inference warnings remain with the bootstrap compiler.

The original identity is public-signed as assembly 4.9.0.0, token
`31bf3856ad364e35`; file version is 4.9.2.0 and informational version includes
the source commit. All 6,176 published public/protected metadata declarations
match, with no missing or extra declarations. Four embedded source byte streams
and all 1,795 neutral resource strings match the independent published metadata
baseline. Windows CRLF representation is derived from the original text sources
for embedded templates and multiline resource values. Published DLLs are read
only as metadata/resource bytes; they are never loaded into an execution context,
compiled against for production output or packaged.

All thirteen translated satellites are built from original XLF sources. The
consumer checks every string in all 14 resource sets (25,130 strings), exact
source identity and consumer-local assembly resolution. The package contains
only this compiler and its satellites; Common remains a separate dependency.

Focused runtime checks cover VB parsing and binding, generic/anonymous types,
LINQ queries, XML literals, iterators, async/await, semantic symbols, actual
analyzer callbacks, portable PDBs, executed emitted IL, compilation errors and
localized diagnostics, source generation and execution, embedded VB runtime
conversion without a normal VB runtime dependency, cancellation and absence of
Framework implementations. These are focused integration gates, not the full
upstream Roslyn unit-test suite. Full PowerShell integration and the runtime's
servicing version remain separate requirements.

Build in CLANG64 or UCRT64 with the source-built SDK, targeting pack and Common/CSharp
4.9.2 packages installed:

```bash
makepkg --cleanbuild --force --noconfirm
```

After installation, use new output directories and only the installed feed:

```bash
bash check.sh NEW_OUTPUT $MINGW_PREFIX/share/doc/dotnet-codeanalysis-visualbasic/localization.json
bash check-api.sh NEW_OUTPUT NEW_API_OUTPUT
```

The metadata tools do not load the inspected assembly. They compare every API,
identity, original neutral resource value and embedded source hash with the
independent baseline. Reference assembly versions differ from the published
net7.0 build because this package targets .NET 8. No normal Visual Basic runtime
reference is allowed in the compiler implementation itself. The SDK's compiler
files remain unchanged.
