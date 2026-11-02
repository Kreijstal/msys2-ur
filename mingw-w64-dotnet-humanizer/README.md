# Source Humanizer.Core 2.14.1

Builds the unchanged Humanizer project and all199 original production C# files
from commit `3ebc38de585fc641a04b0e78ed69468453b0f8a1`. Revision2 adds the original
Standard2.0 target needed by Roslyn Workspaces and retains the preceding NET8
port. Each target compiles independently against its actual installed source
reference pack. No NET6 target is relabeled as NET8.

The original project, sources, signing key, all50 resource sets and three
licenses remain unchanged. Parent versioning/source-link tool imports are
disabled for this source profile. The package supplies explicit version/commit
information and retains the parent's original CommitHash metadata and the
project's target-specific product and neutral-resource attributes.

Fresh Standard2.0 and NET8 consumers restore the exact candidate or installed
NuGet into empty caches. Checks verify the selected framework asset, original
public key, all resource values and original public/protected API declarations
and checked shapes. Casing, irregular inflection, English/German number words,
resources and ordinals execute in an isolated context using exact source build
outputs. The API validation tool uses the installed source Compiler5 libraries;
no private Roslyn/runtime build directory is required. Every producer input is
checked against the archive, cached packages/DLLs against their source feeds,
and both framework assets and all three licenses against build/source bytes.

Run `python make-source.py`, then in Windows CLANG64 run
`MINGW_ARCH=clang64 makepkg-mingw -C -f --noconfirm`.
Installed checks use `check.py ARCHIVE_ROOT PREPARED NEW_CONSUMER TARGET
/clang64/lib/dotnet/library-packs` with TARGET `netstandard2.0` or `net8.0`.

This component does not complete the original Standard1.0/NET6 target variants,
formal Roslyn4.14/4.4 and runtime10 generator packaging, full framework/SDK/
desktop10, PowerShell7.6 integration or other open compatibility gates. Those
remain part of the full dependency objective where required.
