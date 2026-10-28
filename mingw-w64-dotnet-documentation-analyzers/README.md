# DocumentationAnalyzers beta.59 from source

Builds the complete analyzer and code-fix sources at upstream tag commit
489c06575beee224030ffdc9e91ce43569f32a79 for the source-built .NET 8 distribution.
The requested DotNetAnalyzers.DocumentationAnalyzers 1.0.0-beta.59 is a dependency
package; DotNetAnalyzers.DocumentationAnalyzers.Unstable 1.0.0.59 contains both
assemblies, the source-built CommonMark dependency, upstream install scripts and
source files. Both package IDs are produced and dependency selection is tested.

Both assemblies preserve published identity 1.0.0.59/2bc5e20c3ad68793. Upstream's
unstable configuration uses DEVELOPMENT_KEY and DocumentationAnalyzers.dev.snk;
only its public component is derived for PublicSign. Private keys and published
implementation assemblies are not shipped or used as implementation inputs.
The informational version records the exact source commit. Original assembly
attributes and friend access between analyzer and code fixes are retained.

Dependencies are separately source-built Roslyn/CSharp.Workspaces 4.9.2 and
CommonMark.NET 0.15.1. The installed source CSharp compiler49 host is required
for SDK/MSBuild use: the SDK's unchanged 4.8 compiler rejects these 4.9-referencing
analyzers with CS9057. Set CscToolPath to the installed compiler-packs/roslyn-4.9.2
directory and CscToolExe=csc49.cmd, UseSharedCompilation=false. XML documentation
syntax analysis requires GenerateDocumentationFile=true, as PowerShell requests.
The underlying core runtime still uses 8.0.0 sources; servicing remains open.

The public type surface is empty, so public-API count is not used as proof of
analyzer completeness. The independent metadata-only baseline requires all 18
analyzer classes, 14 exported code-fix providers, 18 diagnostic IDs and four
resource sets. Runtime checks instantiate all providers, inspect every descriptor
and compare all 71 source resource strings. Published implementation binaries are
read as metadata only, never loaded for execution, compiled against or packaged.

The fixture extractor compiles with the source-built Roslyn library and derives
inputs/expected fixes from the unmodified pinned upstream test sources, including
inline-data cases and keyword MemberData. All 295 extracted upstream vectors and
one owned empty-langword negative are run, with exact fixed-text comparison
apart from CR/LF normalization. All 18 analyzers and actual code-fix actions of all
14 providers are exercised, including CommonMark-backed Markdown conversion.
The new compiler's keyword enum contains one entry without text spelling; that
is excluded from the recognized-keyword positive provider and covered by the
owned empty-langword rejection test. The extracted corpus is checked against
its versioned baseline. Configured source-test cases verify their resulting
fixed text; this is not a claim to run the original xUnit/test-framework suite or
every compiler-warning span assertion.

A fresh consumer restores only from the installed source feed. Separate actual
MSBuild tests reference only the requested meta-package, require DOC103 for a
negative fixture and require its corrected source to build. Metadata-only
inventories, source/license/payload/dependency audits and source-generated test
corpus gates are included. Framework implementations are rejected.

Build in CLANG64: makepkg --cleanbuild --force --noconfirm
After installing both packages:

    bash mingw-w64-dotnet-documentation-analyzers/check.sh NEW_OUTPUT

Older target frameworks, IDE installation scripts, exhaustive provider/race
coverage and full PowerShell source/application integration remain separate work.
