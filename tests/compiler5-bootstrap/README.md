# Compiler5 bootstrap package validation

The recipe is in `../../mingw-w64-dotnet-compiler5-bootstrap`. Generate its local
source archive with `python make-source.py` from that directory, then build with
`MINGW_ARCH=clang64 makepkg-mingw -C -f --noconfirm` in CLANG64. Both source
archive checksums are pinned in the recipe. The build uses the declared source
SDK, compiler and bootstrap-tools packages, with an empty NuGet feed.

This packages a .NET8 host for the inherited source Compiler5 bootstrap profile,
plus fresh supported net8.0 builds of Immutable9 and Metadata9. It does not
constitute a new complete upstream Roslyn5 build. Compiler bytes are checked
against the declared bootstrap-tools owner; 366 original runtime9 C# inputs and
the projects, resources and notices are checked against the pinned archive.

The recipe check exercises C#14 extension properties, an incremental generator,
a real analyzer callback, runtime9 assembly selection inside the compiler,
emitted execution, Unicode/space response files, and invalid-source exit status.
After installation, `check.py PREPARED NEW_OUTPUT INSTALLED_COMPILER_DIRECTORY`
from the recipe repeats the checks through the installed relative wrapper.

`audit-package.py PACKAGE_ARCHIVE PREPARED OUTPUT_JSON` compares every installed
payload file with its archive bytes, verifies compiler and runtime9 provenance,
checks notices, and limits package files to dedicated compiler, documentation and
license directories. Run it after installing the exact archive. Existing SDK,
Compiler4.9 wrapper and inherited Compiler5 command-line hashes are checked separately.

The dated reports contain exact commands, exit codes, warnings and evidence
hashes. The full PowerShell dependency goal remains open, including remaining
formal generator/library packages and complete .NET10 SDK/runtime integration.
