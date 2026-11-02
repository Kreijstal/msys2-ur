# Original Roslyn4.4 Standard2.0 compiler and Workspaces libraries

Builds Common, CSharp, Workspaces.Common and CSharp.Workspaces from pinned
Roslyn commit `1ce8866c9de4c2d67351ef6863699dee03b0804a`.
All selected original production inputs remain unchanged. The four original
generator tools regenerate five compiler files and three Core operation files;
every output must match its original baseline. IOperationGenerator uses the
original Debug mode because its iterator advances in Debug.Assert; all four
shipping libraries use Release.

The source SDK evaluates the original projects and their shared imports.
Original source-build SQLite exclusion, signing identities, friend/restricted
namespace attributes, complete resource translations, licenses and notices are
retained. The original declared dependency minimums are recorded separately
from the actual source dependency versions used. All producer and consumer
restores use the installed source feed and the current candidate feed only.
A separately compiled Standard2.0 consumer and a NET8 execution harness check
original API/resource baselines, analyzers, incremental generation, emitted IL,
MEF workspaces, cross-project rename, formatting, code fixes and cancellation.

Run `python make-source.py`, then on Windows CLANG64 run
`MINGW_ARCH=clang64 makepkg-mingw -C -f --noconfirm`.
Installed checks use `check.py ARCHIVE_ROOT PREPARED NEW_CONSUMER
/clang64/lib/dotnet/library-packs` and `audit.py ARCHIVE_ROOT PREPARED NEW_CONSUMER`.

Other original target variants, formal runtime10 generators, complete framework,
SDK/desktop10, PowerShell7.6 and all remaining compatibility gates remain open.
