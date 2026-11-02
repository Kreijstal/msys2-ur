# Original Roslyn4.14 Visual Basic prerequisites

Builds the original Standard2.0 VisualBasic compiler and VisualBasic.Workspaces
libraries plus the Microsoft.CodeAnalysis metapackage from Roslyn commit
`8edf7bcd4f1594c3d68a6a567469f41dbd33dd1b`.
All selected original VB/C# production inputs remain unchanged. The three
original generator tools regenerate all five compiler files and the grammar;
every generated output must match the original baseline.

The exact Arcade commit declared by the source manifest supplies the original
VB defaults. Audits verify MyType, strict/infer/explicit/compare settings and
integer-check policy, including the syntax tool's original strict-mode override.
The source profile retains embedded VB runtime behavior, original friend keys,
all resources/translations and embedded source text using Windows line endings.
The original metapackage includes both CSharp and VB Workspaces dependencies.

All dependencies come from installed source compiler/Workspaces4.14, runtime9,
Humanizer and maintenance/reference packages. A fresh consumer through the
metapackage verifies both languages, complete public API/resource baselines,
actual source/cache/consumer DLL bytes, friends, embedded resources, MEF-hosted
VB language services and mixed-language workspace operations. The source SDK
compiler selection remains unchanged.

Run `python make-source.py`, then in Windows CLANG64 run
`MINGW_ARCH=clang64 makepkg-mingw -C -f --noconfirm`.
Installed checks use `check.py ARCHIVE_ROOT PREPARED NEW_CONSUMER
/clang64/lib/dotnet/library-packs` followed by
`audit.py ARCHIVE_ROOT PREPARED NEW_CONSUMER`.

Original NET8/NET9 variants, Roslyn4.4, the complete runtime10 generator bundle,
remaining required dependency targets, full framework/SDK/desktop10,
PowerShell7.6 integration and other open compatibility gates remain part of the
full dependency objective.
