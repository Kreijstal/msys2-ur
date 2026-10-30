# Roslyn Workspaces 4.9.2 from source

Builds `Microsoft.CodeAnalysis.Workspaces.Common` and
`Microsoft.CodeAnalysis.CSharp.Workspaces` 4.9.2 from Roslyn commit
`9934fb9e3527e1c0c51314e57d4aab30f97e8f9e`, matching the upstream package source.
Both target the source-built .NET 8 distribution and depend on the separately
packaged compiler, Humanizer, MEF2 and Pipelines libraries. Channels is supplied
by the .NET 8 shared framework. No SDK/vendor implementation assembly is copied
into these packages.

The complete main source lists and imported shared items are included. The
upstream `DotNetBuildFromSource=true` / `DOTNET_BUILD_FROM_SOURCE` configuration
excludes the optional SQLite persistent-cache implementation and native package.
This is upstream's source-build configuration; no public APIs are stubbed.
It uses non-SQLite storage behavior. A SQLite-enabled build is not claimed.

All normal and restricted friend declarations are preserved, including recursive
key aliases and their allowed external-access namespaces. Assembly identities
are 4.9.0.0/31bf3856ad364e35, public-signed with the upstream MicrosoftShared
public key; this is not a Microsoft private-key signature. File version 4.9.2.0
and the informational source commit identify the build. Resource wrappers are
generated from upstream resx files, retaining their keys, and all XLF satellite
translations are compiled from source.

The independent metadata-only gate compares **1,898** published public/protected
declarations and both assembly identities with no missing or extra entries.
The pinned published package hashes and selected metadata assets are recorded
in `published-metadata-provenance.json`. Published assemblies are never loaded
as implementations, compiled against, or shipped.

The consumer checks actual source identity/location, all exported types, all
expanded friend declarations and all neutral/translated strings. It composes an
MEF-hosted C# AdhocWorkspace, creates Unicode-named documents and project
references, resolves semantic models, finds and renames a symbol across project
boundaries, formats code, applies solution edits and emits a PE. It exercises
simplification, a real analyzer diagnostic, a DocumentEditor-based code fix,
CodeAction/ApplyChanges operations, incremental change tracking and cancellation.
Framework implementation modules are rejected.

Build in CLANG64 or UCRT64 with the source-built SDK and prerequisites installed:

    makepkg --cleanbuild --force --noconfirm

After installing both packages, use new output directories/caches:

    bash mingw-w64-dotnet-roslyn-workspaces/check.sh NEW_CONSUMER $MINGW_PREFIX/share/doc/dotnet-codeanalysis-workspaces-common/localization.json $MINGW_PREFIX/share/doc/dotnet-codeanalysis-workspaces-common/source-items.json
    bash mingw-w64-dotnet-roslyn-workspaces/check-api.sh NEW_CONSUMER NEW_API

Only the installed source-built feed is used unless a new build feed is supplied
explicitly. The current core runtime is still built from 8.0.0 sources; later
servicing and complete PowerShell integration remain required. Visual Basic,
MSBuild/Visual Studio integration and the analyzer packages remain separate work.
Broader workspace/provider/race coverage is not established by these checks.
