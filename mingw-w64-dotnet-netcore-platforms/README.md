# Microsoft.NETCore.Platforms 1.1.2

This data-only package retains the exact upstream runtime.json and netstandard1.0
placeholder from corefx commit 718443a10dbd456b6c8f08ee594a92cfbf2ef8db (v1.1.13).
Its package project declares 1.1.2 and its graph matches the published package's
165 runtime IDs. The corefx v1.1.2 tag has an older, different 117-RID graph and
package version 1.1.0, so it is not used here.

There are no managed/native libraries or runtime dependencies. The source-built
SDK packs the original JSON, license, notices and empty compatibility placeholder.
The consumer restores the exact version from the local feed with a new cache,
verifies every graph byte, and uses the source-built SDK's NuGet runtime model to
expand every RID. It independently checks import closure, cycles and fallback
membership for Windows, Ubuntu/Mint, RHEL and macOS. This preserves the historical
graph requested by PowerShell; it does not replace .NET 8's current SDK graph.

Build in CLANG64 with makepkg --cleanbuild --force --noconfirm. After installation:

    bash check.sh NEW_OUTPUT
