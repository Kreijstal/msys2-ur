# Original Roslyn4.14 Workspaces prerequisites

Builds Microsoft.CodeAnalysis.Workspaces.Common and
Microsoft.CodeAnalysis.CSharp.Workspaces4.14.0 for their original Standard2.0
target from commit `8edf7bcd4f1594c3d68a6a567469f41dbd33dd1b`.
Every selected production C# input remains unchanged. Original projects are
evaluated in Release with source-build settings and central dependency versions.
The original source-build SQLite exclusion is retained. All resources and
translations, signing keys, expanded friend identities and restricted friend
namespaces are preserved and checked.

The workflow uses installed source compiler4.14, runtime9, Humanizer and
maintenance/reference packages. It builds its own evaluator from source and
does not require a private compiler/runtime/Workspaces build directory. Actual
resolved source versions are recorded against original dependency minima.

Fresh consumers verify complete original public API baselines, all98 resource
sets/3,486 strings, exact selected source NuGet/cache/output bytes and original
friend declarations. Real MEF-hosted operations cover Unicode documents,
project references, reference search/rename, formatting, simplification,
analyzers, code-fix registration, CodeAction edits, incremental changes,
cancellation and compilation emit. Source Channels9 exercises backpressure,
multiwriter/reader behavior, errors and cancellation. NET8 selection of original
MEF targets, Humanizer's retained port and the original AsyncInterfaces2.1
forwarder is audited alongside the owned Standard2.0 Workspaces assets.

Run `python make-source.py`, then in Windows CLANG64 run
`MINGW_ARCH=clang64 makepkg-mingw -C -f --noconfirm`.
Installed checks use `check.py ARCHIVE_ROOT PREPARED NEW_CONSUMER
/clang64/lib/dotnet/library-packs`, followed by
`audit.py ARCHIVE_ROOT PREPARED NEW_CONSUMER`.

Original NET8/NET9 Workspaces target variants, VB, Roslyn4.4 and complete
runtime10 shipping generators remain required parts of the full dependency
goal. Complete framework/SDK/desktop10, PowerShell7.6 integration and the other
open compatibility requirements also remain unfinished.
